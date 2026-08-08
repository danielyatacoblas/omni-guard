"""Persistencia y geometría de zonas por video — OMNI Guard.

Tipos de zona:
  - cochera    : espacio de estacionamiento (ocupación + cobro por tiempo)
  - vigilancia : zona protegida (intrusión / merodeo de personas)

Coordenadas NORMALIZADAS (0..1). Archivo: data/zones/<video>.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from .config import config

ZONE_TYPES = ("cochera", "vigilancia")


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def zones_dir() -> Path:
    d = config.data_abs / "zones"
    d.mkdir(parents=True, exist_ok=True)
    return d


def zones_path(video: str) -> Path:
    return zones_dir() / f"{_safe(video)}.json"


def load_config(video: str) -> dict:
    p = zones_path(video)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"video": video, "zones": []}


def save_config(video: str, data: dict) -> dict:
    data = dict(data)
    data["video"] = video
    data.setdefault("zones", [])
    for i, z in enumerate(data["zones"]):
        z.setdefault("id", f"z{i+1}")
        z.setdefault("type", "vigilancia")
        if z["type"] not in ZONE_TYPES:
            z["type"] = "vigilancia"
        z.setdefault("color", "#2D6CDF")
        z.setdefault("name", f"Zona {i+1}")
    zones_path(video).write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
    return data


def zone_to_px(zone: dict, w: int, h: int) -> np.ndarray:
    pts = [(float(x) * w, float(y) * h) for x, y in zone["points"]]
    return np.array(pts, dtype=np.int32)
