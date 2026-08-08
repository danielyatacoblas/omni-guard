"""Procesamiento de un video CCTV en hilo — OMNI Guard.

Mismo patrón que los demás MVPs: lee el video de principio a fin, detecta
(vehículos / personas / rostros), sigue con ByteTrack, actualiza la analítica
del modo activo, dibuja y publica MJPEG + snapshot de estadísticas reales.
"""
from __future__ import annotations

import csv
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import supervision as sv

from .analytics import Analytics, _cobro, _fmt
from .config import config
from .detector import get_detector, mark_warmed
from .zones import load_config

GREEN = (80, 200, 80)
RED = (60, 60, 235)
BLUE = (235, 160, 40)
YELLOW = (40, 190, 235)
WHITE = (240, 240, 240)
DARK = (30, 30, 30)


def _resize_max(frame, max_w):
    if max_w and frame.shape[1] > max_w:
        h, w = frame.shape[:2]
        return cv2.resize(frame, (max_w, int(h * max_w / w)))
    return frame


class VideoProcessor:
    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.running = False
        self.finished = False
        self.latest_jpeg = None
        self.analytics: Analytics | None = None
        self.video = None
        self.cfg_data = None
        self.conf = config.default_conf
        self.progress = 0.0
        self.video_t = 0.0
        self.duration = 0.0
        self.proc_fps = 0.0
        self.detector_kind = config.detector

    # ── primer frame para el editor de zonas ──
    def first_frame_jpeg(self, video_path: str) -> bytes | None:
        cap = cv2.VideoCapture(video_path)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            return None
        frame = _resize_max(frame, config.max_width)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes() if ok else None

    def video_meta(self, video_path: str) -> dict:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return {"fps": round(fps, 2), "frames": n, "width": w, "height": h,
                "duration_sec": round(n / max(1.0, fps), 1)}

    # ── control ──
    def start(self, video_path: str, video_name: str, conf: float,
              detector_kind: str | None = None):
        self.stop()
        self.cfg_data = load_config(video_name)
        self.conf = float(conf)
        self.video = video_name
        self.detector_kind = (detector_kind or config.detector).lower()
        self.finished = False
        self.progress = 0.0
        self.video_t = 0.0
        with self.lock:
            self.latest_jpeg = None
        self.running = True
        self.thread = threading.Thread(target=self._loop, args=(video_path,),
                                       daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.thread = None

    def _make_tracker(self, src_fps: float):
        return sv.ByteTrack(
            track_activation_threshold=config.track_activation,
            lost_track_buffer=config.track_lost_buffer,
            minimum_matching_threshold=config.track_min_match,
            frame_rate=int(round(src_fps)),
        )

    def _process(self, video_path: str, writer=None, log=None, max_frames=0):
        """Bucle común para modo servidor (streaming) y headless (writer)."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"no se pudo abrir {video_path}")
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.duration = total / src_fps if total else 0.0

        ok, frame = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError("video vacío")
        frame = _resize_max(frame, config.max_width)
        h, w = frame.shape[:2]

        detector = get_detector(self.detector_kind)
        tracker = self._make_tracker(src_fps)
        self.analytics = Analytics(self.cfg_data, w, h, src_fps,
                                   mode=self.detector_kind,
                                   video_stem=Path(self.video).stem)
        min_area = config.min_box_area_frac * w * h
        if self.detector_kind == "rostros":
            min_area = 0.0        # los rostros lejanos son diminutos

        out_writer = None
        if writer is not None:
            out_writer = cv2.VideoWriter(
                str(writer), cv2.VideoWriter_fourcc(*"mp4v"), src_fps, (w, h))

        stride = max(1, config.frame_stride)
        dt = stride / src_fps
        frame_idx = 0
        t_wall = time.time()
        proc_count = 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        while True:
            if writer is None and not self.running:
                break
            if max_frames and frame_idx >= max_frames:
                break
            ok = cap.grab()
            if not ok:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            ok, frame = cap.retrieve()
            if not ok:
                break
            frame = _resize_max(frame, config.max_width)
            clean = frame.copy() if self.detector_kind == "rostros" else None

            dets = detector.infer(frame, self.conf)
            dets = self._filter(dets, min_area)
            dets = tracker.update_with_detections(dets)

            self.video_t = frame_idx / src_fps
            self.analytics.update(dets, clean, self.video_t, dt)
            self._draw(frame, dets)
            mark_warmed(self.detector_kind)

            proc_count += 1
            elapsed = time.time() - t_wall
            self.proc_fps = proc_count / elapsed if elapsed > 0 else 0.0
            self.progress = (frame_idx / total) if total else 0.0

            if out_writer is not None:
                out_writer.write(frame)
                if log and frame_idx % 50 == 0 and total:
                    log(f"  frame {frame_idx}/{total} "
                        f"({100*frame_idx/total:.0f}%)  dets {self.analytics.dets_frame}")
            else:
                ok, buf = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, config.jpeg_quality])
                if ok:
                    with self.lock:
                        self.latest_jpeg = buf.tobytes()
            frame_idx += 1

        cap.release()
        if out_writer is not None:
            out_writer.release()

    def _loop(self, video_path: str):
        try:
            self._process(video_path)
        except Exception as e:
            print(f"[processor] error: {e}")
        self.running = False
        self.finished = True
        self.progress = 1.0
        try:
            self.export_csv()
        except Exception as e:
            print(f"[processor] export CSV falló: {e}")

    def _filter(self, dets, min_area):
        if dets is None or len(dets) == 0:
            return dets
        xyxy = dets.xyxy
        areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        return dets[areas >= min_area]

    # ── dibujo ──
    def _draw(self, frame, dets):
        an = self.analytics
        # cocheras
        for c in an.cocheras:
            col = RED if c["estado"] == "ocupada" else GREEN
            overlay = frame.copy()
            cv2.fillPoly(overlay, [c["poly"]], col)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            cv2.polylines(frame, [c["poly"]], True, col, 2)
            p0 = c["poly"][0]
            txt = c["name"] + (f"  {_fmt(c['cur_sec'])} · S/ {_cobro(c['cur_sec']):.2f}"
                               if c["estado"] == "ocupada" else "  LIBRE")
            cv2.putText(frame, txt, (int(p0[0]), int(p0[1]) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2, cv2.LINE_AA)
        # zonas de vigilancia
        for z in an.vigilancia:
            col = RED if z["present"] else BLUE
            overlay = frame.copy()
            cv2.fillPoly(overlay, [z["poly"]], col)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            cv2.polylines(frame, [z["poly"]], True, col, 2)
            p0 = z["poly"][0]
            cv2.putText(frame, f"{z['name']}  [{len(z['present'])}]",
                        (int(p0[0]), int(p0[1]) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2, cv2.LINE_AA)
        # detecciones
        if dets is not None and len(dets):
            tids = dets.tracker_id if dets.tracker_id is not None else [None] * len(dets)
            names = dets.data.get("class_name") if dets.data is not None else None
            for i, (box, tid) in enumerate(zip(dets.xyxy, tids)):
                x1, y1, x2, y2 = map(int, box)
                col = YELLOW if self.detector_kind == "rostros" else BLUE
                cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
                if tid is not None:
                    lbl = f"ID {int(tid)}"
                    if names is not None and self.detector_kind == "vehiculos":
                        lbl = f"{names[i]} {int(tid)}"
                    (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (x1, y1 - th - 5), (x1 + tw + 5, y1), col, -1)
                    cv2.putText(frame, lbl, (x1 + 2, y1 - 3),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, DARK, 1, cv2.LINE_AA)
        # HUD
        extra = ""
        if self.detector_kind == "vehiculos":
            extra = f"ocupadas: {sum(1 for c in an.cocheras if c['estado']=='ocupada')}/{len(an.cocheras)}   S/ {sum(_cobro(c['occupied_sec']) for c in an.cocheras):.2f}"
        elif self.detector_kind == "personas":
            extra = f"intrusiones: {sum(z['intrusiones'] for z in an.vigilancia)}"
        else:
            extra = f"rostros guardados: {len(an.faces)}"
        hud = (f"t {_fmt(self.video_t)} / {_fmt(self.duration)}   "
               f"dets: {an.dets_frame}   {extra}   {self.proc_fps:.1f} fps")
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 26), DARK, -1)
        cv2.putText(frame, hud, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (120, 230, 120), 1, cv2.LINE_AA)

    # ── salidas ──
    def mjpeg_frames(self):
        while True:
            with self.lock:
                data = self.latest_jpeg
            if data is None:
                time.sleep(0.03)
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
            time.sleep(0.04)

    def status(self) -> dict:
        from . import detector as _det
        base = {
            "running": self.running, "finished": self.finished,
            "video": self.video, "progress": round(self.progress, 4),
            "video_time": _fmt(self.video_t), "duration": _fmt(self.duration),
            "proc_fps": round(self.proc_fps, 1),
            "has_frame": self.latest_jpeg is not None,
            "model_ready": _det.is_warmed(self.detector_kind),
            "detector": self.detector_kind,
        }
        if self.analytics:
            base.update(self.analytics.snapshot())
        return base

    def process_to_file(self, video_path: str, video_name: str, conf: float,
                        out_dir: Path, log=print, max_frames: int = 0) -> dict:
        """Modo headless (CLI/test): MP4 anotado + CSV. Devuelve resumen."""
        self.cfg_data = load_config(video_name)
        self.conf = float(conf)
        self.video = video_name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{Path(video_name).stem}_guard.mp4"
        t0 = time.time()
        self._process(video_path, writer=out_file, log=log, max_frames=max_frames)
        csv_path = self.export_csv()
        snap = self.analytics.snapshot()
        log(f"  ✓ {out_file.name} ({out_file.stat().st_size/1e6:.1f} MB)  "
            f"en {time.time()-t0:.1f}s")
        return {"video_out": str(out_file), "csv": str(csv_path),
                "dets_unicos": snap["unicos"],
                "intrusiones": snap["intrusiones"],
                "rostros": snap["rostros_total"],
                "ingresos": snap["ingresos"]}

    def export_csv(self) -> Path:
        if not self.analytics:
            raise RuntimeError("no hay analítica para exportar")
        snap = self.analytics.snapshot()
        out = config.data_abs / f"reporte_{Path(self.video).stem}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["OMNI Guard — Reporte", self.video,
                         f"modo: {self.detector_kind}"])
            wr.writerow([])
            wr.writerow(["RESUMEN"])
            wr.writerow(["Detecciones únicas (tracks)", snap["unicos"]])
            wr.writerow(["Detecciones por frame (prom.)", snap["dets_frame_avg"]])
            wr.writerow(["Pico por frame", snap["peak_frame"]])
            wr.writerow([])
            if snap["cocheras"]:
                wr.writerow(["GARAJE / COCHERAS",
                             f"tarifa S/ {snap['tarifa_hora']:.2f} por hora"])
                wr.writerow(["Cochera", "Estado final", "Ocupaciones",
                             "Tiempo ocupado", "Cobro S/"])
                for c in snap["cocheras"]:
                    wr.writerow([c["name"], c["estado"], c["ocupaciones"],
                                 c["total"], f"{c['cobro_total']:.2f}"])
                wr.writerow(["TOTAL", "", "", "", f"{snap['ingresos']:.2f}"])
                wr.writerow([])
            if snap["vigilancia"]:
                wr.writerow(["VIGILANCIA"])
                wr.writerow(["Zona", "Intrusiones", "Visitantes",
                             "Permanencia máx."])
                for z in snap["vigilancia"]:
                    wr.writerow([z["name"], z["intrusiones"], z["visitantes"],
                                 z["max_dwell"]])
                wr.writerow([])
            if snap["rostros_total"]:
                wr.writerow(["ROSTROS CAPTURADOS", snap["rostros_total"],
                             f"data/rostros/{snap['video_stem']}/"])
                wr.writerow(["ID", "Archivo", "Momento", "Tamaño px"])
                for r in snap["rostros"]:
                    wr.writerow([r["id"], r["file"], r["t"], r["px"]])
                wr.writerow([])
            wr.writerow(["ALERTAS"])
            wr.writerow(["Tiempo video", "Módulo", "Tipo", "Detalle", "Severidad"])
            for a in snap["alerts"]:
                wr.writerow([a["video_time"], a["modulo"], a["tipo"],
                             a["detalle"], a["severity"]])
        return out


processor = VideoProcessor()
