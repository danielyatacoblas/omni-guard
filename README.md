# OMNI Guard — MVP de seguridad para casa y negocio (ApexCorp)

Dashboard funcional de **videovigilancia inteligente** sobre video real de
cámara fija (CCTV). Tres módulos, con **datos reales** (no simulados):

| Módulo | Qué hace | Cliente típico |
| ------ | -------- | -------------- |
| **01 Garaje / Cocheras** | Detecta vehículos, marca cada cochera **libre/ocupada**, mide el tiempo y calcula el **cobro por tarifa horaria** | Cochera/playa de estacionamiento, condominio |
| **02 Vigilancia de zonas** | Detecta personas en zonas dibujadas: alerta de **intrusión** y de **merodeo** | Casa, patio, tienda, almacén |
| **03 Captura de rostros** | Detecta rostros, los sigue y **guarda el recorte** de cada persona que pasó (galería + archivos) | Entrada de casa/negocio |

> **Modelos:** YOLO11n (COCO: vehículos y personas — ya lo tenías del MVP de
> tracking) + **YOLOv8s-face** (adetailer, HuggingFace) para rostros.
> **Aceleración:** CUDA (RTX 3060). No se entrena nada desde 0.

## 1. Instalar

Comparte el **mismo Python global** de los demás MVPs — no hay nada nuevo que
instalar.

```bash
cd first_mvp_seguridad
python download_models.py          # pesos + videos de muestra
```

## 2. Ejecutar

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8030
# o doble clic en arrancar.bat
```

Abre <http://localhost:8030>, elige video, dibuja tus cocheras o zonas
(doble clic para cerrar el polígono) y pulsa **Procesar**.

### Modo headless (sin servidor)

```bash
python run_video.py videos/auto_estaciona.mp4 --detector vehiculos
python run_video.py videos/peatones_arcos.mp4 --detector rostros
python run_video.py videos/entradas.mp4 --detector personas
```

## 3. Ajustes (`.env`)

| Clave | Descripción |
| ----- | ----------- |
| `TARIFA_HORA` | S/ por hora de cochera ocupada (prorrateo por minuto, mín. 1 min) |
| `COCHERA_CONFIRM_SEC` / `COCHERA_FREE_SEC` | Segundos para confirmar ocupada / liberar |
| `INTRUSION_CONFIRM_SEC` | Presencia sostenida que confirma intrusión (1 s) |
| `MERODEO_SEC` | Permanencia que dispara alerta de merodeo (30 s) |
| `FACE_MIN_PX` | Lado mínimo del rostro (px) para guardarlo (28) |
| `FACE_MAX_SAVED` | Tope de capturas por video (200) |
| `DEFAULT_CONF` | Confianza de detección (el slider la sobreescribe) |
| `WORK_RES` | imgsz de inferencia (960: objetos chicos en CCTV) |

## 4. Cómo funciona cada módulo

- **Cocheras**: una cochera pasa a *ocupada* cuando hay un vehículo dentro
  durante `COCHERA_CONFIRM_SEC`; se libera tras `COCHERA_FREE_SEC` vacía.
  Cobro = minutos ocupados × tarifa/60 (mínimo 1 minuto). El polígono y el
  temporizador se dibujan sobre el video.
- **Vigilancia**: una persona "está" en la zona si sus **pies** (base de la
  caja) caen dentro. Intrusión = 1 s dentro (alerta crítica, una vez por
  persona); merodeo = `MERODEO_SEC` sostenidos (alerta warning).
- **Rostros**: cada rostro trackeado ≥ 3 frames y ≥ `FACE_MIN_PX` px se
  recorta (con margen) del frame limpio y se guarda en
  `data/rostros/<video>/rostro_<ID>.jpg`. Si después se ve 1.5× más grande,
  se re-guarda mejor versión. La galería de la UI se llena en vivo.

## 5. Videos de prueba

`download_models.py` trae: garaje techado (`auto_estaciona`), peatones de
frente (`peatones_arcos`), entrada con puertas (`entrada_puertas`) y avenidas
con tráfico (`avenida`, `avenida2` — Roboflow). También sirve cualquier .mp4
de tu propia cámara: cópialo a `videos/`.

## 6. Limitaciones conocidas (MVP)

- Sin re-identificación: si una persona sale y vuelve, cuenta como nueva.
- La captura de rostros necesita rostros ≥ ~28 px (cámara cercana a la entrada).
- El cobro usa el tiempo del video (para demo); en producción sería reloj real.
- Procesa archivos de video; conectar RTSP en vivo es el paso siguiente
  (el patrón ya existe en vision-node).
