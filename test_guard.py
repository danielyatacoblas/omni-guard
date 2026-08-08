#!/usr/bin/env python3
"""Pruebas rápidas del MVP Guard (sin servidor).

    python test_guard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
OK = FAIL = 0

# Se puede correr de dos maneras y cada una entiende el fallo de forma distinta:
# como script (`python test_guard.py`) el resultado es el código de salida, y
# como suite (`pytest`) tiene que ser una excepción. Imprimir «✗» y seguir deja
# a pytest en verde con todo roto, que es peor que no tener pruebas.
BAJO_PYTEST = "pytest" in sys.modules


def check(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ✓ {name}")
        return
    FAIL += 1
    print(f"  ✗ {name} {detail}")
    if BAJO_PYTEST:
        raise AssertionError(f"{name} {detail}".strip())


def falta(que: str, como: str):
    """Lo que no está por no venir en el repositorio no es un fallo: se salta."""
    if BAJO_PYTEST:
        import pytest
        pytest.skip(f"falta {que} — {como}")
    check(f"{que} existe", False, f"— {como}")


def _dets(boxes, tids):
    import numpy as np
    import supervision as sv
    return sv.Detections(
        xyxy=np.array(boxes, dtype=float),
        class_id=np.zeros(len(boxes), dtype=int),
        confidence=np.full(len(boxes), 0.9),
        tracker_id=np.array(tids))


def test_config():
    print("\n[1] Config y pesos")
    from backend.config import config
    check("config carga", config.port == 8030)
    for peso in (config.yolo_model, config.face_model):
        if not (ROOT / peso).exists():
            return falta(peso, "corre download_models.py")
    check("pesos presentes", True)


def test_cochera():
    print("\n[2] Garaje (ocupación y cobro sintéticos)")
    from backend.analytics import Analytics, _cobro
    cfg = {"zones": [{"id": "c1", "name": "C1", "type": "cochera",
                      "points": [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]]}]}
    an = Analytics(cfg, 1000, 1000, 30.0, mode="vehiculos")
    car = _dets([[450, 450, 550, 550]], [1])
    # 4 segundos con auto dentro
    for i in range(120):
        an.update(car, None, i / 30.0, 1 / 30.0)
    c = an.cocheras[0]
    check("cochera pasa a ocupada", c["estado"] == "ocupada")
    check("acumula tiempo", c["occupied_sec"] > 1.0, f"— {c['occupied_sec']:.1f}s")
    check("registra ocupación", c["ocupaciones"] == 1)
    check("alerta de ocupación", any(a["tipo"] == "Cochera ocupada" for a in an.alerts))
    # 3 segundos vacía → libre
    empty = _dets([[50, 50, 90, 90]], [2])
    t0 = 4.0
    for i in range(90):
        an.update(empty, None, t0 + i / 30.0, 1 / 30.0)
    check("cochera se libera", an.cocheras[0]["estado"] == "libre")
    check("alerta con cobro", any("S/" in a["detalle"] for a in an.alerts))
    check("cobro > 0", _cobro(c["occupied_sec"]) > 0)


def test_vigilancia():
    print("\n[3] Vigilancia (intrusión y merodeo sintéticos)")
    from backend.analytics import Analytics
    from backend.config import config
    cfg = {"zones": [{"id": "v1", "name": "Patio", "type": "vigilancia",
                      "points": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]}]}
    an = Analytics(cfg, 1000, 1000, 30.0, mode="personas")
    person = _dets([[400, 300, 500, 600]], [7])   # pies en (450, 600) dentro
    frames = int((config.merodeo_sec + 2) * 30)
    for i in range(frames):
        an.update(person, None, i / 30.0, 1 / 30.0)
    z = an.vigilancia[0]
    check("intrusión detectada", z["intrusiones"] == 1)
    check("alerta crítica", any(a["severity"] == "critical" for a in an.alerts))
    check("merodeo detectado", any(a["tipo"] == "Merodeo" for a in an.alerts))


def test_rostros_video():
    print("\n[4] Rostros en video real (80 frames, peatones_arcos)")
    vid = ROOT / "videos" / "peatones_arcos.mp4"
    if not vid.exists():
        return falta("videos/peatones_arcos.mp4", "corre download_models.py")
    import shutil
    from backend.config import config
    from backend.processor import VideoProcessor
    faces_dir = config.faces_abs / "peatones_arcos"
    shutil.rmtree(faces_dir, ignore_errors=True)
    p = VideoProcessor()
    p.detector_kind = "rostros"
    res = p.process_to_file(str(vid), vid.name, 0.3, ROOT / "outputs",
                            log=lambda *a: None, max_frames=80)
    check("procesa sin errores", True)
    check("captura rostros", res["rostros"] > 3, f"— {res['rostros']}")
    saved = list(faces_dir.glob("*.jpg"))
    check("guarda archivos jpg", len(saved) >= 3, f"— {len(saved)}")
    check("CSV creado", Path(res["csv"]).exists())
    csv_txt = Path(res["csv"]).read_text(encoding="utf-8")
    check("CSV lista rostros", "ROSTROS CAPTURADOS" in csv_txt)


def test_garaje_video():
    print("\n[5] Garaje en video real (auto_estaciona con zona)")
    vid = ROOT / "videos" / "auto_estaciona.mp4"
    zjson = ROOT / "data" / "zones" / "auto_estaciona.mp4.json"
    if not (vid.exists() and zjson.exists()):
        return falta("videos/auto_estaciona.mp4 y su zona",
                     "corre download_models.py")
    from backend.processor import VideoProcessor
    p = VideoProcessor()
    p.detector_kind = "vehiculos"
    res = p.process_to_file(str(vid), vid.name, 0.3, ROOT / "outputs",
                            log=lambda *a: None, max_frames=300)
    check("procesa sin errores", True)
    check("detecta vehículos", res["dets_unicos"] > 0, f"— {res['dets_unicos']}")
    check("genera ingresos", res["ingresos"] > 0, f"— S/ {res['ingresos']}")


def main():
    print("=== Test OMNI Guard MVP ===")
    test_config()
    test_cochera()
    test_vigilancia()
    test_rostros_video()
    test_garaje_video()
    print(f"\nResultado: {OK} OK · {FAIL} FALLOS")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
