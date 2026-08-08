# OMNI Guard — seguridad para casa y negocio

> **Visión computacional · YOLO11 + ByteTrack · FastAPI · CUDA o CPU**
>
> ![estado](https://img.shields.io/badge/estado-MVP%20funcional-2D6CDF)
> ![version](https://img.shields.io/badge/versión-v0.3.0-129A6B)
> ![pruebas](https://img.shields.io/badge/pruebas-20%20comprobaciones-129A6B)
> ![licencia](https://img.shields.io/badge/uso-interno%20ApexCorp-E19100)

![OMNI Guard en marcha](docs/capturas/01-garaje.png)

## El problema

Una cámara de seguridad graba. No avisa. Alguien tiene que estar mirando la
pantalla, o revisar las horas de grabación después de que ya pasó algo.

Y en una cochera de barrio, el cobro se lleva en un cuaderno: quién entró, a
qué hora, cuánto debe. Se discute, se olvida, se pierde.

OMNI Guard hace las dos cosas sobre el mismo video: **avisa mientras pasa** y
**cobra por tiempo sin que nadie apunte nada**.

| Módulo | Qué responde | Con qué |
|---|---|---|
| **Garaje** | ¿Qué plaza está ocupada, desde cuándo, y cuánto se debe? | Zonas por plaza; el cobro sale del tiempo dentro |
| **Vigilancia** | ¿Alguien entró donde no debía? ¿Alguien lleva rato dando vueltas? | Zonas de intrusión y umbral de merodeo |
| **Rostros** | ¿Quién pasó por la entrada? | Recorte de cara con `face_yolov8s` a partir de ~28 px |

## Qué se ve

| | |
|---|---|
| **Cochera con cobro por tiempo**<br><img src="docs/capturas/01-garaje.png" width="100%"><br><sub>plazas ocupadas, tiempo dentro e importe acumulado</sub> | **Vigilancia**<br><img src="docs/capturas/02-vigilancia.png" width="100%"><br><sub>intrusión y merodeo sobre zonas dibujadas</sub> |
| **Editor de zonas**<br><img src="docs/capturas/03-editor-de-zonas.png" width="100%"><br><sub>una plaza es un polígono; se dibuja una vez</sub> |  |

## Cómo funciona

<a href="docs/flujo.svg">
  <img src="docs/flujo.svg" alt="De la grabación al aviso" width="100%">
</a>

<sub>Ábrelo en grande: <a href="docs/flujo.svg"><code>docs/flujo.svg</code></a>.
Las cifras de las tarjetas no están escritas a mano — las pone
<a href="scripts/diagrama.py"><code>scripts/diagrama.py</code></a> leyendo
<code>docs/modelos.json</code>, que a su vez genera
<a href="scripts/medir_modelos.py"><code>scripts/medir_modelos.py</code></a>
midiendo los modelos de verdad. Si mañana se cambia un modelo, se corren los
dos y el dibujo se corrige solo.</sub>

### El mismo recorrido, en corto

```mermaid
flowchart LR
  V["Video de cámara"] --> P["Lector de fotogramas"]
  P --> D["YOLO11n<br/>personas y vehículos"]
  D --> T["ByteTrack"]
  T --> R["Reglas"]
  R --> R1["Intrusión: entra en zona vetada"]
  R --> R2["Merodeo: sigue dentro pasado el umbral"]
  R --> R3["Cochera: entra, ocupa, sale → tarifa"]
  P --> F["face_yolov8s<br/>recorte de rostro"]
  R --> M["Anotado + MJPEG"]
  R --> C["CSV y alertas"]
```

**El cobro usa el tiempo del video, no el reloj.** Para la demo es lo correcto:
un video de 30 segundos tiene que producir un importe comprobable. En
producción se cambia por reloj real, y es una línea.

**El merodeo necesita un umbral, no una detección.** Nadie «merodea» en un
fotograma: se detecta estando dentro de la zona más tiempo del razonable. Ese
umbral es lo único que separa una alarma útil de una que suena cada vez que
alguien se ata un zapato.

<!-- MODELOS:inicio -->

### Los modelos, medidos

| Modelo | Para qué | Entrada | Precisión | Recall | mAP@50 | mAP@50-95 |
|---|---|---|---|---|---|---|
| **`yolo11n.pt`** | Personas y vehículos | 640² | 65.6 % | 50.2 % | 55.1 % | 39.4 % |
| **`face_yolov8s.pt`** | Rostros, para el recorte de la entrada | 640² | — | — | — | — |

<sub>Estas cuatro columnas **no** se calculan aquí: salen del propio archivo `.pt`, donde Ultralytics guarda la validación del entrenamiento que produjo esos pesos. Son el acierto sobre el conjunto de validación de quien lo entrenó, **no** sobre los videos de este proyecto. Medir eso exigiría etiquetar a mano esta operación concreta, que es trabajo que un MVP todavía no ha hecho; dar un porcentaje inventado sería peor que no darlo. Comprobación de que la lectura es correcta: `yolo11n` sale con mAP@50-95 = 39,4 % y Ultralytics publica 39,5 % para ese modelo en COCO.</sub>

### De dónde sale cada modelo

| Modelo | Entrenado sobre | Épocas | Resolución | Origen |
|---|---|---|---|---|
| **`yolo11n.pt`** | `coco` | 600 | 640×640 | [Ultralytics · COCO 2017](https://docs.ultralytics.com/models/yolo11/) |
| **`face_yolov8s.pt`** | `data` | 100 | 640×640 | Detector de rostro de adetailer |

<sub>El conjunto, las épocas y la resolución salen de `train_args`, que Ultralytics guarda dentro del propio `.pt`. Es decir: no es lo que dice la documentación del modelo, es lo que quedó grabado en el archivo que este repositorio usa de verdad. Los nombres de conjunto son los del disco de quien entrenó —`retrain_data`, `safe_human`— porque es literalmente lo que hay dentro.</sub>

| Modelo | Parámetros | Clases | Latencia (mejor) | Latencia (mediana) | Det./fotograma | Confianza media |
|---|---|---|---|---|---|---|
| **`yolo11n.pt`** | 2.6 M | 80 | 16.6 ms · 60 fps | 20.0 ms · 50.0 fps | 1.4 | 0.632 |
| **`face_yolov8s.pt`** | 11.1 M | 1 | 21.4 ms · 47 fps | 25.4 ms · 39.4 fps | 12.5 | 0.706 |

<sub>Esto sí se mide aquí, con <a href="scripts/medir_modelos.py"><code>scripts/medir_modelos.py</code></a>, sobre fotogramas reales de los videos del repositorio, en una RTX 3060 Laptop y a la resolución que usa la aplicación. Sesenta fotogramas, descartando los veinte primeros.<br>Se dan <b>dos</b> latencias a propósito. Esta GPU está a 210 MHz en reposo y tarda segundos en subir de reloj, así que la mediana se mueve bastante entre pasadas —el mismo <code>yolo11n</code> ha dado 20 y 48 fps— mientras que el mejor caso es estable y representa lo que la máquina puede sostener. Dar solo la cifra buena sería vender de más; dar solo la mediana, castigar al modelo por la gestión de energía del portátil.</sub>

<!-- MODELOS:fin -->

## Datos personales

**Los recortes de rostro no se versionan.** Son datos biométricos de personas
reales que nunca dieron su consentimiento — en varios videos de prueba salen de
la calle. Publicarlos en un repositorio abierto no es un problema de tamaño:
expone a personas identificables, y en Perú lo cubre la **Ley 29733** de
protección de datos personales.

El código que los produce sí está aquí. Las caras no, y por eso no hay ninguna
captura de la galería de rostros en este README.

## Probarlo

```bash
pip install -r requirements.txt
python download_models.py
python -m uvicorn backend.main:app --port 8030    # o arrancar.bat
```

### Por qué los pesos y los videos no están aquí

No son código: son la entrada y la salida del sistema. Varios pasan de los
100 MB que GitHub rechaza de plano, y clonar el proyecto pasaría de segundos a
minutos para traerse archivos que se regeneran o se descargan.

```bash
python download_models.py          # los recupera y dice cuáles faltan
```

## Cómo está montado

```
backend/
├── config.py     todo por variable de entorno, tarifa incluida
├── detector.py   personas/vehículos y rostros, cargados al usarse
├── processor.py  el bucle: leer, detectar, seguir, anotar, emitir
├── analytics.py  reglas de intrusión y merodeo + cálculo del cobro
├── zones.py      plazas y zonas vetadas, guardadas en 0..1
└── main.py       API, MJPEG y galería de rostros
frontend/         interfaz sin framework
scripts/          generadores de las capturas y del diagrama de ramas
run_video.py      procesa un video entero a archivo, sin navegador
```

## Ajustes (`.env`)

| Clave | Para qué |
|---|---|
| `DEVICE` | `cuda` o `cpu` |
| `TARIFA_HORA` | Precio por hora de la cochera |
| `LOITER_SEC` | Segundos dentro de zona que cuentan como merodeo |
| `FACE_MIN_PX` | Tamaño mínimo de cara para intentar el recorte |
| `WORK_RES` | Resolución de inferencia |

## Pruebas

```bash
python -m pytest -q
```

Veinte comprobaciones en cinco bloques: config y pesos, ocupación de cochera y
**cobro por tiempo**, intrusión y merodeo sobre recorridos sintéticos, captura
de rostros en 80 fotogramas reales, y una pasada de garaje de 300 fotogramas
que tiene que acabar generando ingresos.

Un detector que falla se ve en pantalla; una regla de merodeo mal puesta no —
solo suena de más, o no suena nunca. Lo que falta por no venir en el
repositorio se **salta**, no se da por bueno.

<!-- GITFLOW:inicio -->

## Cómo se trabajó

**10 commits**, **6 fusiones** y **3 etiquetas** (`v0.1.0`, `v0.2.0`, `v0.3.0`). al generar este bloque. Cada rama entra con `--no-ff`: un merge aplastado ahorra una línea y borra la única prueba de que aquello fue una tarea con principio y final.

```mermaid
gitGraph
   commit id: "import"
   branch develop
   checkout develop
   branch feature/repository-hygiene
   checkout feature/repository-hygiene
   commit
   checkout develop
   merge feature/repository-hygiene
   checkout main
   merge develop tag: "v0.1.0"
   checkout develop
   branch feature/tests-that-actually-fail
   checkout feature/tests-that-actually-fail
   commit
   checkout develop
   merge feature/tests-that-actually-fail
   checkout main
   merge develop tag: "v0.2.0"
   checkout develop
   branch feature/documentation
   checkout feature/documentation
   commit
   checkout develop
   merge feature/documentation
   checkout main
   merge develop tag: "v0.3.0"
```

| Prefijo | Para qué | Ramas |
|---|---|---|
| `feature/` | trabajo acotado, se integra en develop | 3 |
| `develop/` | rama de integración | 3 |

| Rama | Responsabilidad | Regla de salida |
|---|---|---|
| `main` | Lo que ve primero quien llega al repositorio | Solo recibe trabajo terminado y con las pruebas en verde |
| `develop` | Integración: aquí se junta todo antes de subir | Merge `--no-ff` desde una rama `feature/*` |
| `feature/*` | Un trabajo acotado, nombrado por lo que hace | Merge `--no-ff` a `develop` con sus pruebas escritas |

Los mensajes siguen *Conventional Commits* y están en inglés. Explican **por qué**, no qué: el *qué* ya está en el diff. Varios cuentan el fallo que arreglan y cómo se descubrió, que es lo que sirve dentro de seis meses.

<sub>El diagrama lo genera <a href="scripts/gitflow.py"><code>scripts/gitflow.py</code></a> leyendo <code>git log --merges</code>.</sub>

<!-- GITFLOW:fin -->

---

## Licencia

Uso interno de ApexCorp S.A.C.

<sub>OMNI Guard · ApexCorp S.A.C. — desarrollado por
<a href="https://github.com/danielyatacoblas">Daniel Yataco Blas</a></sub>
