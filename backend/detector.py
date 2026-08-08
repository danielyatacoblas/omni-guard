"""Detectores intercambiables → detecciones Supervision — OMNI Guard.

Backends (seleccionables en runtime desde la UI):
  - vehiculos : YOLO11n COCO (car, motorcycle, bus, truck) — garaje/cocheras.
  - personas  : YOLO11n COCO (person) — vigilancia de zonas.
  - rostros   : YOLOv8s-face (adetailer) — captura de rostros.

Todos aplican NMS class-agnostic.
"""
from __future__ import annotations

import os
from pathlib import Path

import supervision as sv

from .config import config

if config.device.lower() == "cpu":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

ROOT = Path(__file__).resolve().parent.parent

VEHICLE_CLASSES = [2, 3, 5, 7]     # car, motorcycle, bus, truck (COCO)
PERSON_CLASSES = [0]

KINDS = ("vehiculos", "personas", "rostros")
LABELS = {
    "vehiculos": "YOLO11n · vehículos (garaje)",
    "personas": "YOLO11n · personas (vigilancia)",
    "rostros": "YOLOv8s-face · rostros (captura)",
}


def _round_res(x: int, base: int = 32) -> int:
    x = max(base * 7, int(x))
    return int(round(x / base) * base)


def _nms(dets):
    if dets is not None and len(dets):
        try:
            return dets.with_nms(threshold=config.nms_iou, class_agnostic=True)
        except Exception:
            pass
    return dets


def _dev():
    import torch
    return 0 if (config.device.lower().startswith("cuda")
                 and torch.cuda.is_available()) else "cpu"


def _resolve(p_str: str) -> Path:
    p = Path(p_str)
    if not p.is_absolute():
        p = ROOT / p_str
    if not p.exists():
        raise FileNotFoundError(
            f"no se encontró {p} — ejecuta: python download_models.py")
    return p


class Detector:
    def __init__(self, kind: str):
        self.kind = kind if kind in KINDS else "vehiculos"
        self.resolution = _round_res(config.work_res)
        self.device = _dev()
        from ultralytics import YOLO
        if self.kind == "rostros":
            self.model = YOLO(str(_resolve(config.face_model)))
            self.classes = None
        else:
            self.model = YOLO(str(_resolve(config.yolo_model)))
            self.classes = (VEHICLE_CLASSES if self.kind == "vehiculos"
                            else PERSON_CLASSES)
        self.variant = Path(
            config.face_model if self.kind == "rostros" else config.yolo_model).stem

    def infer(self, frame, conf: float):
        r = self.model.predict(frame, conf=conf, classes=self.classes,
                               device=self.device, imgsz=self.resolution,
                               verbose=False)[0]
        return _nms(sv.Detections.from_ultralytics(r))


# ── caché por tipo + estado de "warmed" ──
_cache: dict[str, Detector] = {}
_warmed: set[str] = set()


def get_detector(kind: str | None = None) -> Detector:
    kind = (kind or config.detector or "vehiculos").lower()
    if kind not in KINDS:
        kind = "vehiculos"
    if kind not in _cache:
        _cache[kind] = Detector(kind)
    return _cache[kind]


def mark_warmed(kind: str):
    _warmed.add(kind)


def is_warmed(kind: str | None = None) -> bool:
    kind = (kind or config.detector or "vehiculos").lower()
    return kind in _warmed
