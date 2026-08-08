"""Carga de configuración desde .env — OMNI Guard (seguridad doméstica/PYME)."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _f(key, default):
    return float(os.getenv(key, default))


def _i(key, default):
    return int(os.getenv(key, default))


def _b(key, default):
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    # modelos
    detector: str = os.getenv("DETECTOR", "vehiculos").lower()  # vehiculos | personas | rostros
    yolo_model: str = os.getenv("YOLO_MODEL", "weights/yolo11n.pt")
    face_model: str = os.getenv("FACE_MODEL", "weights/face_yolov8s.pt")
    device: str = os.getenv("DEVICE", "cuda")
    work_res: int = _i("WORK_RES", 960)     # imgsz (960: autos/caras chicas en CCTV)
    default_conf: float = _f("DEFAULT_CONF", 0.30)
    nms_iou: float = _f("NMS_IOU", 0.6)

    # tracking (ByteTrack) — cámara FIJA (CCTV)
    track_activation: float = _f("TRACK_ACTIVATION", 0.25)
    track_lost_buffer: int = _i("TRACK_LOST_BUFFER", 60)
    track_min_match: float = _f("TRACK_MIN_MATCH", 0.75)
    min_track_frames: int = _i("MIN_TRACK_FRAMES", 3)
    min_box_area_frac: float = _f("MIN_BOX_AREA_FRAC", 0.0002)

    # procesamiento
    frame_stride: int = _i("FRAME_STRIDE", 1)
    max_width: int = _i("MAX_WIDTH", 1280)
    jpeg_quality: int = _i("JPEG_QUALITY", 80)

    # garaje / cocheras
    tarifa_hora: float = _f("TARIFA_HORA", 5.0)       # S/ por hora de ocupación
    cochera_confirm_sec: float = _f("COCHERA_CONFIRM_SEC", 2.0)  # seg. para confirmar ocupada
    cochera_free_sec: float = _f("COCHERA_FREE_SEC", 2.0)        # seg. vacía para liberar

    # vigilancia
    intrusion_confirm_sec: float = _f("INTRUSION_CONFIRM_SEC", 1.0)  # presencia para alertar
    merodeo_sec: float = _f("MERODEO_SEC", 30.0)      # permanencia que dispara "merodeo"

    # rostros
    face_min_px: int = _i("FACE_MIN_PX", 28)          # lado mínimo del rostro para guardarlo
    face_confirm_frames: int = _i("FACE_CONFIRM_FRAMES", 3)
    face_max_saved: int = _i("FACE_MAX_SAVED", 200)   # tope de capturas por video
    face_margin: float = _f("FACE_MARGIN", 0.35)      # margen alrededor del rostro al recortar

    # servidor
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _i("PORT", 8030)
    videos_dir: str = os.getenv("VIDEOS_DIR", "videos")
    data_dir: str = os.getenv("DATA_DIR", "data")

    @property
    def videos_abs(self) -> Path:
        p = Path(self.videos_dir)
        return p if p.is_absolute() else ROOT / p

    @property
    def data_abs(self) -> Path:
        p = Path(self.data_dir)
        return p if p.is_absolute() else ROOT / p

    @property
    def faces_abs(self) -> Path:
        return self.data_abs / "rostros"


config = Config()
config.data_abs.mkdir(parents=True, exist_ok=True)
config.videos_abs.mkdir(parents=True, exist_ok=True)
config.faces_abs.mkdir(parents=True, exist_ok=True)
