#!/usr/bin/env python3
"""Descarga los pesos (YOLO11n + YOLOv8s-face) y videos de muestra.

Uso:
    python download_models.py            # pesos + videos
    python download_models.py --no-video # solo pesos
    python download_models.py --only-video
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
WEIGHTS = ROOT / "weights"
VIDEOS = ROOT / "videos"
WEIGHTS.mkdir(exist_ok=True)
VIDEOS.mkdir(exist_ok=True)

FACE_URL = "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8s.pt"
FACE_DST = WEIGHTS / "face_yolov8s.pt"

VIDEO_URLS = {
    "auto_estaciona.mp4":   # garaje techado, un auto llega y se estaciona
        "https://videos.pexels.com/video-files/4707190/4707190-hd_1920_1080_24fps.mp4",
    "peatones_arcos.mp4":   # peatones de frente (rostros visibles)
        "https://videos.pexels.com/video-files/855564/855564-hd_1920_1080_24fps.mp4",
    "entrada_puertas.mp4":  # gente entrando/saliendo por puertas
        "https://videos.pexels.com/video-files/9206570/9206570-hd_1920_1080_25fps.mp4",
}


def _fetch(url: str, dst: Path):
    if dst.exists() and dst.stat().st_size > 1e6:
        print(f"  · {dst.name} ya existe — omitido")
        return
    print(f"  ↓ {dst.name} ...")
    urllib.request.urlretrieve(url, dst)
    print(f"  ✓ {dst.name} ({dst.stat().st_size/1e6:.1f} MB)")


def download_weights():
    print("→ Pesos ...")
    try:
        _fetch(FACE_URL, FACE_DST)
    except Exception as e:
        print(f"  ✗ face: {e}")
    try:
        from ultralytics import YOLO
        dst = WEIGHTS / "yolo11n.pt"
        if not dst.exists():
            YOLO("yolo11n.pt")   # descarga a cwd/caché
            src = Path("yolo11n.pt")
            if src.exists():
                src.replace(dst)
        print("  ✓ yolo11n listo")
    except Exception as e:
        print(f"  ✗ yolo11n: {e}")


def download_videos():
    print("→ Videos de muestra (Pexels + Roboflow) ...")
    for name, url in VIDEO_URLS.items():
        try:
            _fetch(url, VIDEOS / name)
        except Exception as e:
            print(f"  ✗ {name}: {e}")
    # avenidas con vehículos (Roboflow/Supervision)
    try:
        from supervision.assets import VideoAssets, download_assets
        import shutil
        for asset, name in ((VideoAssets.VEHICLES, "avenida.mp4"),
                            (VideoAssets.VEHICLES_2, "avenida2.mp4")):
            dst = VIDEOS / name
            if dst.exists():
                continue
            f = Path(download_assets(asset))
            if not f.exists():
                f = ROOT / f.name
            shutil.move(str(f), str(dst))
            print(f"  ✓ {name}")
    except Exception as e:
        print(f"  · supervision assets: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--only-video", action="store_true")
    a = ap.parse_args()
    if not a.only_video:
        download_weights()
    if not a.no_video:
        download_videos()
    print("\nListo. Arranca el servidor con:  uvicorn backend.main:app --port 8030")


if __name__ == "__main__":
    sys.exit(main())
