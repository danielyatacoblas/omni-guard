"""Analítica real por video — OMNI Guard (garaje, vigilancia, rostros).

Todo se calcula sobre el *tiempo del video* (frame / fps), no sobre el reloj
de pared, igual que en los demás MVPs.

- Garaje (modo vehiculos): por cochera dibujada → estado libre/ocupada con
  confirmación temporal, tiempo ocupado acumulado y COBRO por tarifa horaria.
- Vigilancia (modo personas): por zona → intrusión (persona confirmada dentro)
  y merodeo (permanencia sostenida). Alertas reales.
- Rostros (modo rostros): captura y guarda el recorte de cada rostro trackeado
  (el de mayor tamaño visto por track) en data/rostros/<video>/.
"""
from __future__ import annotations

import cv2
import numpy as np

from .config import config
from .zones import zone_to_px


class Analytics:
    def __init__(self, cfg_data: dict, w: int, h: int, fps: float,
                 mode: str, video_stem: str = "video"):
        self.w, self.h, self.fps = w, h, max(1.0, fps)
        self.mode = mode                      # vehiculos | personas | rostros
        self.video_stem = video_stem

        # ── zonas ──
        self.cocheras = []
        self.vigilancia = []
        for z in cfg_data.get("zones", []):
            poly = zone_to_px(z, w, h)
            if len(poly) < 3:
                continue
            entry = {"id": z.get("id"), "name": z.get("name", "Zona"),
                     "color": z.get("color", "#2D6CDF"), "poly": poly}
            if z.get("type") == "cochera":
                entry.update({
                    "estado": "libre", "since": None,     # t de cambio candidato
                    "occupied_sec": 0.0,                  # tiempo ocupado total
                    "ocupaciones": 0, "cur_sec": 0.0,     # ocupación en curso
                    "empty_since": None,
                })
                self.cocheras.append(entry)
            else:
                entry.update({
                    "dwell": {},          # tid -> segundos dentro
                    "present": set(),
                    "intrusiones": 0,
                    "_alerted": set(),    # tids ya alertados (intrusión)
                    "_merodeo": set(),    # tids ya alertados (merodeo)
                })
                self.vigilancia.append(entry)

        # rostros
        self.faces = []            # [{id, file, t, px}] capturas guardadas
        self._face_best = {}       # tid -> área guardada
        self.faces_dir = config.faces_abs / video_stem
        if mode == "rostros":
            self.faces_dir.mkdir(parents=True, exist_ok=True)

        # estado común
        self.tracks = {}           # tid -> {frames, first, last}
        self.dets_frame = 0
        self.dets_frame_avg = 0.0
        self.peak_frame = 0
        self.unicos = 0            # tracks confirmados
        self.cur_t = 0.0
        self.timeline = []
        self._last_sample_sec = -1
        self.alerts = []

    # ── helpers ──
    def _add_alert(self, t, modulo, tipo, detalle, severity):
        self.alerts.append({"t": round(t, 1), "video_time": _fmt(t),
                            "modulo": modulo, "tipo": tipo,
                            "detalle": detalle, "severity": severity})

    @staticmethod
    def _inside(poly, cx, cy) -> bool:
        return cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0

    # ── actualización por frame (detections trackeadas + frame limpio) ──
    def update(self, detections, clean_frame, video_t: float, dt: float):
        self.cur_t = video_t

        items = []   # (cx, cy, box, tid)
        if detections is not None and len(detections):
            tids = (detections.tracker_id if detections.tracker_id is not None
                    else [None] * len(detections))
            for box, tid in zip(detections.xyxy, tids):
                cx = (box[0] + box[2]) / 2.0
                cy = (box[1] + box[3]) / 2.0
                items.append((cx, cy, box, tid))

        # tracks únicos confirmados
        for _, _, _, tid in items:
            if tid is None:
                continue
            tid = int(tid)
            tr = self.tracks.get(tid)
            if tr is None:
                self.tracks[tid] = {"frames": 1, "first": video_t,
                                    "last": video_t, "confirmed": False}
            else:
                tr["frames"] += 1
                tr["last"] = video_t
                if not tr["confirmed"] and tr["frames"] >= config.min_track_frames:
                    tr["confirmed"] = True
                    self.unicos += 1

        self.dets_frame = len(items)
        self.peak_frame = max(self.peak_frame, self.dets_frame)
        self.dets_frame_avg = (0.9 * self.dets_frame_avg + 0.1 * self.dets_frame
                               if self.dets_frame_avg else float(self.dets_frame))

        if self.mode == "vehiculos":
            self._update_cocheras(items, video_t, dt)
        elif self.mode == "personas":
            self._update_vigilancia(items, video_t, dt)
        else:
            self._update_rostros(items, clean_frame, video_t)

        sec = int(video_t)
        if sec != self._last_sample_sec:
            self._last_sample_sec = sec
            self.timeline.append({"t": sec, "dets": self.dets_frame,
                                  "ocupadas": sum(1 for c in self.cocheras
                                                  if c["estado"] == "ocupada"),
                                  "rostros": len(self.faces)})

    # ── garaje ──
    def _update_cocheras(self, items, video_t, dt):
        for c in self.cocheras:
            occupied_now = any(self._inside(c["poly"], cx, cy)
                               for cx, cy, _, _ in items)
            if c["estado"] == "libre":
                if occupied_now:
                    if c["since"] is None:
                        c["since"] = video_t
                    elif video_t - c["since"] >= config.cochera_confirm_sec:
                        c["estado"] = "ocupada"
                        c["ocupaciones"] += 1
                        c["cur_sec"] = video_t - c["since"]
                        c["empty_since"] = None
                        self._add_alert(video_t, "Garaje", "Cochera ocupada",
                                        f"{c['name']} — vehículo estacionado",
                                        "info")
                else:
                    c["since"] = None
            else:  # ocupada
                c["cur_sec"] += dt
                c["occupied_sec"] += dt
                if occupied_now:
                    c["empty_since"] = None
                else:
                    if c["empty_since"] is None:
                        c["empty_since"] = video_t
                    elif video_t - c["empty_since"] >= config.cochera_free_sec:
                        c["estado"] = "libre"
                        c["since"] = None
                        cobro = _cobro(c["cur_sec"])
                        self._add_alert(
                            video_t, "Garaje", "Cochera liberada",
                            f"{c['name']} — {_fmt(c['cur_sec'])} ocupada · "
                            f"S/ {cobro:.2f}", "info")
                        c["cur_sec"] = 0.0

    # ── vigilancia ──
    def _update_vigilancia(self, items, video_t, dt):
        for z in self.vigilancia:
            present = set()
            for cx, cy, box, tid in items:
                # una persona "está" en la zona si sus PIES caen dentro
                foot_y = box[3]
                if not self._inside(z["poly"], cx, foot_y):
                    continue
                if tid is None:
                    continue
                tid = int(tid)
                present.add(tid)
                z["dwell"][tid] = z["dwell"].get(tid, 0.0) + dt
                d = z["dwell"][tid]
                if d >= config.intrusion_confirm_sec and tid not in z["_alerted"]:
                    z["_alerted"].add(tid)
                    z["intrusiones"] += 1
                    self._add_alert(video_t, "Vigilancia", "Intrusión",
                                    f"{z['name']} — persona ID {tid} dentro",
                                    "critical")
                if d >= config.merodeo_sec and tid not in z["_merodeo"]:
                    z["_merodeo"].add(tid)
                    self._add_alert(video_t, "Vigilancia", "Merodeo",
                                    f"{z['name']} — ID {tid} lleva {_fmt(d)}",
                                    "warning")
            z["present"] = present

    # ── rostros ──
    def _update_rostros(self, items, clean_frame, video_t):
        if clean_frame is None or len(self.faces) >= config.face_max_saved:
            return
        for cx, cy, box, tid in items:
            if tid is None:
                continue
            tid = int(tid)
            tr = self.tracks.get(tid)
            if tr is None or not tr["confirmed"]:
                continue
            x1, y1, x2, y2 = map(int, box)
            side = min(x2 - x1, y2 - y1)
            if side < config.face_min_px:
                continue
            area = (x2 - x1) * (y2 - y1)
            best = self._face_best.get(tid, 0)
            # guarda la primera vez; re-guarda si el rostro se ve 1.5x más grande
            if best and area < best * 1.5:
                continue
            m = config.face_margin
            mx = int((x2 - x1) * m); my = int((y2 - y1) * m)
            cx1 = max(0, x1 - mx); cy1 = max(0, y1 - my)
            cx2 = min(self.w, x2 + mx); cy2 = min(self.h, y2 + my)
            crop = clean_frame[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue
            fname = f"rostro_{tid:04d}.jpg"
            cv2.imwrite(str(self.faces_dir / fname), crop,
                        [cv2.IMWRITE_JPEG_QUALITY, 92])
            if not best:
                self.faces.append({"id": tid, "file": fname,
                                   "t": _fmt(video_t), "px": side})
                self._add_alert(video_t, "Rostros", "Rostro capturado",
                                f"ID {tid} guardado ({side}px)", "info")
            else:
                for f in self.faces:
                    if f["id"] == tid:
                        f["px"] = side
                        f["t"] = _fmt(video_t)
            self._face_best[tid] = area

    # ── snapshot para el dashboard ──
    def snapshot(self) -> dict:
        cocheras_out = []
        for c in self.cocheras:
            cobro_cur = _cobro(c["cur_sec"]) if c["estado"] == "ocupada" else 0.0
            cocheras_out.append({
                "id": c["id"], "name": c["name"], "color": c["color"],
                "estado": c["estado"],
                "cur": _fmt(c["cur_sec"]) if c["estado"] == "ocupada" else "—",
                "cur_sec": round(c["cur_sec"], 1),
                "total": _fmt(c["occupied_sec"]),
                "ocupaciones": c["ocupaciones"],
                "cobro_cur": round(cobro_cur, 2),
                "cobro_total": round(_cobro(c["occupied_sec"]), 2),
            })
        vig_out = [{
            "id": z["id"], "name": z["name"], "color": z["color"],
            "present": len(z["present"]),
            "intrusiones": z["intrusiones"],
            "max_dwell": _fmt(max(z["dwell"].values())) if z["dwell"] else "0s",
            "visitantes": len(z["dwell"]),
        } for z in self.vigilancia]

        return {
            "mode": self.mode,
            "dets_frame": self.dets_frame,
            "dets_frame_avg": round(self.dets_frame_avg, 1),
            "peak_frame": self.peak_frame,
            "unicos": self.unicos,
            "cocheras": cocheras_out,
            "ocupadas": sum(1 for c in self.cocheras if c["estado"] == "ocupada"),
            "ingresos": round(sum(c["cobro_total"] for c in cocheras_out), 2),
            "tarifa_hora": config.tarifa_hora,
            "vigilancia": vig_out,
            "intrusiones": sum(z["intrusiones"] for z in self.vigilancia),
            "rostros": self.faces[-60:][::-1],
            "rostros_total": len(self.faces),
            "video_stem": self.video_stem,
            "timeline": self.timeline[-600:],
            "alerts": self.alerts[-100:],
        }


def _cobro(sec: float) -> float:
    """Cobro por tiempo: tarifa horaria prorrateada por minuto (mín. 1 min)."""
    if sec <= 0:
        return 0.0
    minutos = max(1.0, sec / 60.0)
    return minutos * config.tarifa_hora / 60.0


def _fmt(sec: float) -> str:
    sec = int(round(sec))
    m, s = divmod(sec, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s" if m else f"{s}s"
