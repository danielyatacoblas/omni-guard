#!/usr/bin/env python3
"""Procesa un video en modo headless (sin servidor) — MP4 anotado + CSV en outputs/.

Uso:
    python run_video.py videos/auto_estaciona.mp4 --detector vehiculos
    python run_video.py videos/peatones_arcos.mp4 --detector rostros --max-frames 100
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.processor import processor

ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="ruta al .mp4")
    ap.add_argument("--conf", type=float, default=None)
    ap.add_argument("--detector", default=None,
                    choices=["vehiculos", "personas", "rostros"])
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--out", default="outputs")
    a = ap.parse_args()

    from backend.config import config
    p = Path(a.video)
    if not p.is_absolute():
        p = ROOT / a.video
    if not p.exists():
        raise SystemExit(f"no existe: {p}")
    if a.detector:
        processor.detector_kind = a.detector
    conf = a.conf if a.conf is not None else config.default_conf

    print(f"→ Procesando {p.name} (conf={conf}, detector={processor.detector_kind})")
    res = processor.process_to_file(str(p), p.name, conf, ROOT / a.out,
                                    max_frames=a.max_frames)
    print(f"\nResumen: unicos={res['dets_unicos']}  intrusiones={res['intrusiones']}  "
          f"rostros={res['rostros']}  ingresos=S/ {res['ingresos']:.2f}")
    print(f"Video anotado: {res['video_out']}")
    print(f"CSV: {res['csv']}")


if __name__ == "__main__":
    main()
