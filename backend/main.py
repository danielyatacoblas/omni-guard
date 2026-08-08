"""Servidor FastAPI — OMNI Guard (garaje, vigilancia, rostros).

Rutas:
  GET  /                     -> dashboard
  GET  /api/videos           -> lista de videos + config
  GET  /api/video/{name}/meta-> metadatos
  GET  /api/video/{name}/frame -> primer frame JPEG (editor de zonas)
  GET  /api/video/{name}/zones -> zonas guardadas
  POST /api/video/{name}/zones -> guarda zonas
  POST /api/start            -> inicia {video, conf, detector}
  POST /api/stop             -> detiene
  GET  /stream               -> MJPEG anotado
  GET  /api/status           -> snapshot de estadísticas reales
  GET  /api/export           -> CSV
  GET  /rostros/...          -> capturas de rostros (estático)
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles

from .config import config
from .processor import processor
from .zones import load_config, save_config

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
VIDEO_EXT = (".mp4", ".avi", ".mov", ".mkv", ".webm")

app = FastAPI(title="OMNI Guard — MVP seguridad")


@app.on_event("startup")
def _warmup():
    """Precarga los detectores en segundo plano (elimina arranque en frío)."""
    import threading

    def _load():
        import numpy as np
        from .detector import get_detector, mark_warmed
        dummy = np.zeros((720, 1280, 3), dtype=np.uint8)
        for kind in dict.fromkeys([config.detector, "vehiculos", "personas",
                                   "rostros"]):
            try:
                d = get_detector(kind)
                d.infer(dummy, config.default_conf)
                d.infer(dummy, config.default_conf)
                mark_warmed(d.kind)
                print(f"[warmup] detector '{d.kind}' precargado y listo")
            except Exception as e:
                print(f"[warmup] no se pudo precargar '{kind}': {e}")

    threading.Thread(target=_load, daemon=True).start()


@app.get("/api/videos")
def list_videos():
    vids = []
    if config.videos_abs.exists():
        vids = sorted(f.name for f in config.videos_abs.iterdir()
                      if f.suffix.lower() in VIDEO_EXT)
    from .detector import KINDS, LABELS
    return {"videos": vids, "default_conf": config.default_conf,
            "device": config.device,
            "detectors": [{"kind": k, "label": LABELS[k]} for k in KINDS],
            "default_detector": config.detector,
            "tarifa_hora": config.tarifa_hora,
            "merodeo_sec": config.merodeo_sec}


def _vpath(name: str) -> Path:
    return config.videos_abs / name


@app.get("/api/video/{name}/meta")
def video_meta(name: str):
    p = _vpath(name)
    if not p.exists():
        return JSONResponse({"error": "video no encontrado"}, status_code=404)
    return processor.video_meta(str(p))


@app.get("/api/video/{name}/frame")
def video_frame(name: str):
    p = _vpath(name)
    if not p.exists():
        return JSONResponse({"error": "video no encontrado"}, status_code=404)
    jpg = processor.first_frame_jpeg(str(p))
    if jpg is None:
        return JSONResponse({"error": "no se pudo leer el frame"}, status_code=400)
    return Response(content=jpg, media_type="image/jpeg")


@app.get("/api/video/{name}/zones")
def get_zones(name: str):
    return load_config(name)


@app.post("/api/video/{name}/zones")
async def set_zones(name: str, request: Request):
    data = await request.json()
    return save_config(name, data)


@app.post("/api/start")
async def start(request: Request):
    body = await request.json()
    name = body.get("video")
    conf = float(body.get("conf", config.default_conf))
    detector = body.get("detector") or config.detector
    p = _vpath(name) if name else None
    if not p or not p.exists():
        return JSONResponse({"error": "video no encontrado"}, status_code=404)
    try:
        processor.start(str(p), name, conf, detector)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return {"ok": True, "video": name, "detector": detector}


@app.post("/api/stop")
def stop():
    processor.stop()
    return {"ok": True}


@app.get("/stream")
def stream():
    return StreamingResponse(
        processor.mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/status")
def status():
    return processor.status()


@app.get("/api/export")
def export():
    try:
        out = processor.export_csv()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return FileResponse(str(out), media_type="text/csv", filename=out.name)


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/rostros", StaticFiles(directory=config.faces_abs), name="rostros")
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
