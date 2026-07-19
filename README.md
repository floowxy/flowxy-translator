<div align="center">

```
███████╗██╗      ██████╗ ██╗    ██╗██╗  ██╗██╗   ██╗
██╔════╝██║     ██╔═══██╗██║    ██║╚██╗██╔╝╚██╗ ██╔╝
█████╗  ██║     ██║   ██║██║ █╗ ██║ ╚███╔╝  ╚████╔╝ 
██╔══╝  ██║     ██║   ██║██║███╗██║ ██╔██╗   ╚██╔╝  
██║     ███████╗╚██████╔╝╚███╔███╔╝██╔╝ ██╗   ██║   
╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝  
                    T R A N S L A T O R
```

**Transcripción y traducción de video con aceleración GPU**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%2012.1-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![Whisper](https://img.shields.io/badge/Whisper-medium-412991?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![NLLB](https://img.shields.io/badge/NLLB-1.3B-0467DF?style=for-the-badge&logo=meta&logoColor=white)](https://ai.meta.com/research/no-language-left-behind/)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

### **[📖 Documentación completa → floowxy.github.io/flowxy-translator](https://floowxy.github.io/flowxy-translator/)**

</div>

---

## ¿Qué es esto?

Flowxy-Translator convierte videos de YouTube (o archivos locales) en material de estudio interactivo. Descarga, transcribe y traduce con GPU, y te entrega un reproductor con subtítulos sincronizados palabra a palabra o un video MP4 con subtítulos quemados de calidad profesional.

Pensado para **desarrolladores que aprenden inglés técnico** leyendo código mientras escuchan al autor.

Todo corre **100% en local**: los modelos viven en tu disco y ningún dato sale de tu máquina (salvo la descarga del video y el TTS opcional de Edge).

---

## Pipeline de procesamiento

```
URL de YouTube  ·  Archivo local (MP4/MKV/WebM/MP3…)
      │                    │
      ▼                    ▼
┌─────────────┐     yt-dlp / upload      ┌──────────────┐
│   Download  │ ────────────────────────▶│  downloads/  │
│  o Upload   │                          │  {id}_video  │
└─────────────┘                          └──────┬───────┘
                                                │
                                                ▼
                                         ┌──────────────┐   word_timestamps=True
                                         │   Whisper    │◀─ beam=5, best_of=5
                                         │   medium     │   no_speech=0.6
                                         │   GPU ↔ CPU  │   float16
                                         └──────┬───────┘
                                                │ segmentos + timestamps por PALABRA
                                                ▼
                                         ┌──────────────┐   DP grouper: agrupa
                                         │  NLLB 1.3B   │◀─ segmentos en oraciones
                                         │  context-    │   completas + memoria
                                         │  aware       │   inter-grupo
                                         │  GPU ↔ CPU   │   beam=5, float16
                                         └──────┬───────┘
                                                │ traducción por grupo semántico
                         ┌──────────────────────┼──────────────────────┐
                         ▼                      ▼                      ▼
                 ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
                 │  Reproductor │      │  Video MP4   │      │  Subtítulos  │
                 │  word        │      │  cues 42×2   │      │  SRT / VTT   │
                 │  highlight   │      │  alineados   │      │  JSON / TXT  │
                 │              │      │  al habla    │      │  bilingüe    │
                 └──────────────┘      └──────────────┘      └──────────────┘
```

Cada resultado intermedio se guarda en **caché de dos capas** (RAM + disco), así que repetir cualquier paso es instantáneo, incluso tras reiniciar el servidor.

---

## Traducción con contexto — DP grouper

Traducir subtítulo a subtítulo destroza la calidad: Whisper corta el habla en trozos de ~5 s que rara vez son oraciones completas. En su lugar, el **DP grouper** (`_dp_group_segments` en `nllb_engine.py`) agrupa los segmentos en unidades semánticas antes de traducir, con 4 señales de cierre de grupo:

1. El texto termina en `.!?` → oración completa
2. El grupo acumula 60 palabras → evitar truncado del modelo
3. El siguiente segmento abre con conector (`"However,"`, `"But "`, `"Now "`, …) → nuevo pensamiento
4. Silencio ≥ 0.5 s entre segmentos → pausa natural

Cada grupo se traduce como texto unificado, y el texto del grupo anterior se pasa como **contexto inter-grupo** (pronombres, referencias, continuidad del discurso). Un post-procesado limpia los artefactos típicos de NLLB (`"hola ."` → `"hola."`, artículos duplicados, espacios múltiples).

`NLLB_CONTEXT_AWARE = False` en `config.py` desactiva todo esto y usa batch puro (más rápido, menos calidad).

---

## Subtítulos alineados al habla

El problema clásico de los subtítulos traducidos automáticamente: frases cortadas a la mitad, muros de texto y desfase con lo que el hablante dice. `build_translated_cues()` (`backend/export/srt_exporter.py`) lo resuelve reconstruyendo los cues desde cero:

```
Traducción del grupo (una o varias oraciones)
      │
      ▼  1. División por oraciones (.!?…); las largas se parten
      │     balanceadas con preferencia por comas — NUNCA a
      │     mitad de frase. Máx 84 chars (2 líneas × 42).
      ▼
┌────────────────────┬──────────────────┬─────────────────────┐
│ "La gente lo ama   │ "sumergirse en   │ "raspar páginas web │
│  por su versatili- │  la ciencia de   │  o simplemente..."  │
│  dad, ..."         │  datos,"         │                     │
└─────────┬──────────┴────────┬─────────┴──────────┬──────────┘
          ▼                   ▼                    ▼
      2. Cada cue se ancla al intervalo de las palabras FUENTE
         que le corresponden (proporcional por caracteres sobre
         los word timestamps de Whisper) → el subtítulo aparece
         MIENTRAS el hablante dice esa parte.
          │
          ▼
      3. Pase de legibilidad: duración mínima 1 s, extensión
         hacia los silencios si hay mucho texto (CPS > 20),
         cierre de micro-huecos, sin solapes.
```

Reglas de presentación (estándar de la industria):

| Regla | Valor |
|---|---|
| Líneas por subtítulo | máx 2 |
| Caracteres por línea | máx 42 |
| Velocidad de lectura | ≤ 20 CPS (se extiende hacia pausas si se supera) |
| Duración por cue | 1 – 6 s |
| Cortes de texto | solo en límites de oración o cláusula |

Este sistema se aplica al **video quemado**, al **SRT descargable** y al **VTT** cuando se exporta la traducción. Si un caché antiguo no trae word timestamps, se degrada a interpolación lineal sin romper nada.

---

## Gestión de VRAM — Offload automático GPU ↔ CPU

Con 8 GB de VRAM (RTX 4060 Ti), Whisper medium (~1.5 GB) y NLLB 1.3B (~2.6 GB) se alternan automáticamente:

```
VRAM (8 GB)
│
│  [Transcripción]              [Traducción]
│  ┌─────────────────┐          ┌─────────────────┐
│  │  Whisper (GPU)  │    →     │  Whisper (CPU)  │
│  │  NLLB    (CPU)  │          │  NLLB    (GPU)  │
│  └─────────────────┘          └─────────────────┘
│         ▲                            ▲
│         └── torch.cuda.empty_cache() en cada cambio
```

- **Precarga**: al arrancar, ambos modelos se cargan en RAM (`preload_to_cpu`) — el primer request no paga cold-start de carga desde disco.
- **`gpu_lock`** (`backend/utils/gpu_lock.py`): mutex async compartido entre todos los endpoints REST y el WebSocket — serializa el acceso a GPU y evita OOM con requests concurrentes.
- **Revalidación de caché tras el lock**: dos requests idénticos en paralelo no ejecutan Whisper/NLLB dos veces; el segundo encuentra el resultado ya cacheado.

---

## Caché en dos capas

| Capa | Dónde | Qué guarda |
|---|---|---|
| RAM | dicts LRU (20 entradas c/u) | transcripciones y traducciones de la sesión |
| Disco | `downloads/{stem}_transcription.json`<br>`downloads/{stem}_translation_{lang}.json` | sobrevive reinicios y `--reload` |

Todos los endpoints siguen el patrón *memoria → disco*: si el resultado existe en cualquiera de las capas, se reutiliza. El historial (`/api/history`) restaura una sesión completa en <1 s.

---

## Características

| Característica | Detalle |
|---|---|
| **Descarga** | yt-dlp, video individual (no playlists), sufijo `_video` / `_audio` |
| **Upload local** | MP4, MKV, WebM, MP3… con drag & drop (`POST /api/upload`) |
| **Transcripción** | Whisper medium, timestamps por palabra, filtrado de no-habla nativo |
| **Traducción** | NLLB-200 1.3B context-aware con DP grouper y memoria inter-grupo |
| **Reproductor** | Word highlighting sincronizado, modos original / traducido / bilingüe |
| **Export video** | Subtítulos quemados con cues alineados al habla (42×2, CPS controlado) |
| **Export texto** | SRT, VTT, JSON, TXT — simple o bilingüe |
| **Doblaje TTS** | Edge-TTS opcional, clips ajustados exactamente al timeline *(experimental, en stand-by)* |
| **Historial** | Lista de videos procesados con preview e idiomas; restaura sesión desde disco |
| **Progreso real** | `GET /api/progress/{task_id}` — Whisper, NLLB y FFmpeg reportan avance real |
| **Gestión** | Borrar archivos (`DELETE /api/files`), re-traducir limpiando caché |
| **GPU stats** | Polling adaptativo: cada 4 s durante tareas, 30 s en idle |
| **WebSocket** | Subtítulos en tiempo real para extensión de Chrome |
| **Seguridad** | Path traversal protection, CORS restringido, validación Pydantic |

---

## Stack técnico

<details>
<summary><strong>Backend</strong></summary>

| Paquete | Rol |
|---|---|
| `fastapi` + `uvicorn` | Framework web asíncrono + servidor ASGI |
| `pydantic` v2 | Validación de requests |
| `websockets` | Subtítulos en tiempo real |
| `aiofiles` | I/O asíncrono de archivos |

Todo el trabajo pesado (yt-dlp, Whisper, NLLB, FFmpeg, uploads) corre en `asyncio.to_thread` — nada bloquea el event loop.

</details>

<details>
<summary><strong>IA y Machine Learning</strong></summary>

| Paquete | Rol |
|---|---|
| `torch` + `torchaudio` (CUDA 12.1) | Backend de inferencia |
| `openai-whisper` | Transcripción (modelo medium, word timestamps) |
| `transformers` | NLLB-200-1.3B vía HuggingFace |
| `sentencepiece` | Tokenización NLLB |

</details>

<details>
<summary><strong>Audio, Video y Utilidades</strong></summary>

| Paquete | Rol |
|---|---|
| `yt-dlp` | Descarga de video |
| `edge-tts` | Doblaje TTS (opcional) |
| `av`, `librosa`, `soundfile`, `pydub` | Procesamiento de audio/video |
| FFmpeg (sistema) | Quemado de subtítulos, concat TTS, probes |

</details>

<details>
<summary><strong>Frontend</strong></summary>

React + Vite + TypeScript. FastAPI sirve el build estático de `frontend/dist/` — en producción no corre ningún proceso Node. Diseño "Studio Dark" con tipografía display auto-hosteada.

</details>

---

## Instalación

### Requisitos

| Componente | Mínimo | Recomendado |
|---|---|---|
| Python | 3.11 | 3.12 |
| CUDA Toolkit | 12.1 | 12.1+ |
| FFmpeg | 6.0 | 6.0+ |
| RAM | 16 GB | 32 GB |
| VRAM | 6 GB | 8 GB |
| Disco | 20 GB libres | 40 GB |

> Sin GPU NVIDIA el sistema funciona en CPU, solo más lento.

### Linux / macOS

```bash
# 1. Dependencias del sistema
sudo apt install python3.11 python3.11-venv ffmpeg git  # Ubuntu/Debian
brew install python@3.11 ffmpeg git                      # macOS

# 2. Clonar
git clone <repo-url>
cd flowxy-translator

# 3. Entorno virtual
python3.11 -m venv .venv
source .venv/bin/activate        # fish: source .venv/bin/activate.fish

# 4. Dependencias Python
pip install --upgrade pip
pip install -r requirements.txt

# 5. Verificar GPU
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 6. Compilar el frontend (React + Vite; Node solo se usa para el build)
cd frontend && npm install && npm run build && cd ..

# 7. Arrancar
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload
```

### Windows (PowerShell)

```powershell
# Si los scripts están bloqueados:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 1. Instalar Python 3.11 desde python.org, CUDA 12.1+ desde nvidia.com, FFmpeg:
winget install FFmpeg

# 2. Clonar y configurar
git clone <repo-url>
cd flowxy-translator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# 3. Compilar el frontend (requiere Node.js)
cd frontend; npm install; npm run build; cd ..

# 4. Arrancar
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload
```

Luego abre `http://localhost:9000`.

> Los modelos (~4 GB en total) se descargan automáticamente en `models/` la primera vez.
>
> **Desarrollo del frontend**: `cd frontend && npm run dev` levanta Vite en `:5173`
> con hot-reload, proxeando la API al backend en `:9000`. El build compilado en
> `frontend/dist/` está commiteado, así que solo necesitas Node si vas a modificar la UI.

---

## Configuración — `backend/config.py`

```python
# ── Modelos ─────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE = "medium"   # tiny | base | small | medium | large-v2 | large-v3
NLLB_MODEL_SIZE    = "1.3B"     # "600M" | "1.3B"
COMPUTE_TYPE       = "float16"  # float16 | int8_float16 | int8 | float32
DEVICE             = "auto"     # "auto" | "cuda" | "cpu"

# ── Whisper ─────────────────────────────────────────────────────────
WHISPER_BEAM_SIZE                   = 5
WHISPER_BEST_OF                     = 5
WHISPER_NO_SPEECH_THRESHOLD         = 0.6   # descarta segmentos sin habla
WHISPER_COMPRESSION_RATIO_THRESHOLD = 2.4   # descarta segmentos "garbage"

# ── NLLB ────────────────────────────────────────────────────────────
NLLB_BEAM_SIZE          = 5      # calidad vs velocidad
NLLB_BATCH_SIZE         = 16     # solo en modo batch (context_aware=False)
NLLB_MAX_LENGTH         = 512
NLLB_REPETITION_PENALTY = 1.1
NLLB_NO_REPEAT_NGRAM    = 4
NLLB_CONTEXT_AWARE      = True   # DP grouper + memoria inter-grupo

# ── Subtítulos ──────────────────────────────────────────────────────
SRT_MAX_CHARS_PER_LINE = 42      # estándar de legibilidad
SRT_MAX_LINES          = 2

# ── Servidor ────────────────────────────────────────────────────────
SERVER_PORT  = 9000              # evita conflicto con otros servicios locales
CORS_ORIGINS = []                # frontend en el mismo origen — sin cross-origin
```

### Reducir uso de VRAM (GPU pequeña o CPU)

```python
WHISPER_MODEL_SIZE = "small"     # ~500 MB VRAM
NLLB_MODEL_SIZE    = "600M"      # ~1.2 GB VRAM
COMPUTE_TYPE       = "int8"
NLLB_BATCH_SIZE    = 8
```

---

## API — Endpoints

```
GET    /                              → Frontend (index.html)
GET    /player                        → Reproductor con subtítulos
GET    /health                        → Health check
GET    /api/gpu-stats                 → Estado de la GPU (VRAM, CUDA info)
GET    /api/progress/{task_id}        → Progreso real de la tarea (0.0 – 1.0)

POST   /api/download                  → Descarga video/audio de YouTube
POST   /api/upload                    → Sube archivo local (MP4, MKV, WebM, MP3…)
POST   /api/transcribe                → Transcribe con Whisper (word timestamps)
POST   /api/translate                 → Traduce texto suelto
POST   /api/translate-transcript      → Traduce transcripción completa (DP grouper)
POST   /api/export                    → Exporta SRT / VTT / JSON / TXT (± bilingüe)
POST   /api/export-video              → Exporta MP4 con subtítulos quemados ± TTS

GET    /api/subtitles/{file}          → Segmentos con timestamps para el player
GET    /api/history                   → Videos procesados (preview + idiomas)
GET    /api/export/{file}             → Descarga archivo exportado
GET    /audio/{file}                  → Sirve audio descargado
GET    /video/{file}                  → Sirve video descargado

DELETE /api/files/{file}              → Borra media + cachés + exports
DELETE /api/cache/translation/{file}  → Limpia caché de traducción (re-traducir)

WS     /ws                            → WebSocket tiempo real (extensión Chrome)
```

Los exports llevan sufijo por idioma (`_es`, `_bilingual`) para que las variantes no se sobreescriban entre sí.

---

## Uso paso a paso

**1 · Obtener el video**
- Pega una URL de YouTube (con "Descargar VIDEO COMPLETO" activo para usar el reproductor), **o**
- Arrastra un archivo local (MP4, MKV, WebM, MP3…)

**2 · Transcribir**
- Selecciona idioma o deja auto-detect
- Whisper genera segmentos con timestamps por palabra
- Resultado cacheado en RAM y disco

**3 · Traducir**
- Selecciona idioma destino (español por defecto)
- El DP grouper traduce oración por oración con contexto
- El botón *Re-traducir* limpia el caché y vuelve a traducir

**4 · Reproducir**
- Reproductor integrado con word highlighting sincronizado
- Modos original / traducido / bilingüe en vivo

**5 · Exportar**
- **Video MP4** con subtítulos quemados alineados al habla
- **Video MP4** con subtítulos + doblaje Edge-TTS *(experimental)*
- **SRT / VTT** con los mismos cues de calidad que el video
- **JSON / TXT** con transcripción y traducción completas

**6 · Historial**
- Cualquier video procesado antes se restaura completo en <1 s desde el caché en disco

---

## Rendimiento

### RTX 4060 Ti 8 GB + Ryzen 5 7600X + 32 GB RAM

| Tarea | Tiempo |
|---|---|
| Transcripción (medium, 10 min de video) | ~50–100 s |
| Traducción context-aware (1.3B, 10 min) | ~1–2 min |
| Export video solo subtítulos | ~30 s |
| Export video + TTS | ~2–3 min |
| **Total para video de 10 min** | **~3–5 min** |
| Repetir cualquier paso (caché) | <1 s |

### Solo CPU (i7 / Ryzen 7)

| Tarea | Tiempo |
|---|---|
| Transcripción (medium, 10 min de video) | ~5–10 min |
| Traducción (1.3B, 10 min) | ~5–10 min |
| Export video solo subtítulos | ~2–3 min |
| **Total para video de 10 min** | **~15–25 min** |

---

## Estructura del proyecto

```
flowxy-translator/
│
├── backend/
│   ├── config.py                  # Configuración central + helpers GPU
│   ├── main.py                    # App FastAPI, endpoints, caché 2 capas, WebSocket
│   │
│   ├── whisper/
│   │   ├── whisper_engine.py      # Carga/offload, transcripción con word timestamps
│   │   ├── whisper_stream.py
│   │   └── whisper_utils.py
│   │
│   ├── translation/
│   │   ├── nllb_engine.py         # DP grouper, memoria inter-grupo, postproceso
│   │   ├── translation_utils.py
│   │   └── language_detect.py
│   │
│   ├── export/
│   │   ├── srt_exporter.py        # build_translated_cues (cues alineados al habla),
│   │   │                          #   SRT simple y bilingüe
│   │   ├── vtt_exporter.py        # VTT simple y bilingüe
│   │   ├── transcript_export.py   # JSON / TXT / TXT bilingüe
│   │   └── video_export.py        # FFmpeg quemado + Edge-TTS ajustado al timeline
│   │
│   ├── websocket/
│   │   └── realtime_handler.py    # Subtítulos en tiempo real (extensión Chrome)
│   │
│   └── utils/
│       ├── gpu_lock.py            # Mutex async — serializa acceso a GPU
│       ├── gpu_stats.py           # VRAM, CUDA info
│       ├── logger.py
│       ├── timers.py
│       └── chunker.py
│
├── frontend/                      # React + Vite + TypeScript (Studio Dark)
│   ├── index.html                 # Entry de la UI principal
│   ├── player.html                # Entry del reproductor
│   ├── vite.config.ts             # Dev proxy a :9000 + build multi-página
│   ├── src/
│   │   ├── App.tsx                # Orquestación del flujo (estado global)
│   │   ├── api.ts                 # Cliente HTTP tipado (contrato con FastAPI)
│   │   ├── types.ts               # Tipos compartidos de la API
│   │   ├── components/            # Una sección del flujo por componente
│   │   └── player/PlayerApp.tsx   # Reproductor + word highlighting
│   └── dist/                      # Build servido por FastAPI (npm run build)
│
├── downloads/                     # Media descargada/subida + cachés JSON
├── exports/                       # MP4, SRT, VTT, JSON exportados
├── models/
│   ├── whisper/                   # Whisper medium (~1.5 GB, auto-descarga)
│   └── nllb/                      # NLLB-200-1.3B (~2.6 GB, auto-descarga)
│
├── cookies.txt                    # (Opcional) Cookies del navegador para yt-dlp
├── requirements.txt
└── LICENSE
```

---

## Seguridad

- **Path traversal**: `_safe_filename()` valida cada nombre de archivo recibido por la API — rechaza `../`, rutas absolutas y caracteres peligrosos antes de tocar el disco
- **CORS**: `CORS_ORIGINS = []` — el frontend se sirve desde el mismo origen que la API; no hay acceso cross-origin (importante porque `SERVER_HOST="0.0.0.0"` expone el servidor a la red local)
- **Cookies**: `cookies.txt` solo lo lee yt-dlp localmente; ningún endpoint lo expone
- **Input validation**: todos los requests se validan con Pydantic v2
- **Escape de HTML** en el historial del frontend

---

## Solución de problemas

<details>
<summary><strong>CUDA no detectado</strong></summary>

```bash
nvidia-smi                                          # Verificar driver
python -c "import torch; print(torch.cuda.is_available())"

# Reinstalar PyTorch con CUDA 12.1
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

</details>

<details>
<summary><strong>Memoria GPU insuficiente (OOM)</strong></summary>

```python
# backend/config.py
WHISPER_MODEL_SIZE = "small"    # ~500 MB VRAM
NLLB_MODEL_SIZE    = "600M"     # ~1.2 GB VRAM
COMPUTE_TYPE       = "int8"
NLLB_BATCH_SIZE    = 4
```

El offload automático ya evita el caso más común (ambos modelos en GPU a la vez).

</details>

<details>
<summary><strong>YouTube bloquea la descarga</strong></summary>

Exporta las cookies de tu navegador a un archivo `cookies.txt` en la raíz del proyecto. El servidor lo detecta automáticamente en cada descarga.

</details>

<details>
<summary><strong>Los subtítulos del video exportado no coinciden con el audio</strong></summary>

Si la traducción viene de un caché antiguo (sin word timestamps), el sistema degrada a interpolación lineal. Borra el caché de traducción (`DELETE /api/cache/translation/{file}` o el botón *Re-traducir*) y vuelve a traducir para regenerar los datos completos.

</details>

<details>
<summary><strong>Video no se reproduce en el player</strong></summary>

El reproductor necesita el archivo de **video completo** (no solo audio). Asegúrate de haber marcado "Descargar VIDEO COMPLETO" al descargar.

</details>

<details>
<summary><strong>Puerto 9000 en uso</strong></summary>

```bash
# Linux/macOS
lsof -i :9000 && kill -9 $(lsof -ti:9000)

# Windows
netstat -ano | findstr :9000
taskkill /PID <PID> /F
```

O cambia `SERVER_PORT` en `backend/config.py`.

</details>

<details>
<summary><strong>Primera ejecución muy lenta</strong></summary>

Los modelos se descargan una sola vez:
- Whisper medium → ~1.5 GB en `models/whisper/`
- NLLB 1.3B → ~2.6 GB en `models/nllb/`

Después, ambos se precargan en RAM al arrancar el servidor — el primer request ya no paga cold-start.

</details>

---

## ¿La traducción es literal?

No. NLLB-200 traduce por **contexto y significado**, y el DP grouper le da oraciones completas con memoria del discurso anterior:

```
Original:  "I'm gonna grab a bite before we dive into the code"
Literal:   "Voy a agarrar un mordisco antes de que nos sumerjamos en el código"
NLLB:      "Voy a comer algo antes de meternos con el código"
```

El modelo reorganiza frases, adapta expresiones idiomáticas y mantiene el tono técnico del contenido.

> **Límite conocido**: cuando NLLB reordena mucho una oración larga, el subtítulo puede adelantarse o atrasarse ~1 frase respecto al audio — es inherente a alinear una traducción reordenada con el habla original.

---

<div align="center">

**[Documentación completa](https://floowxy.github.io/flowxy-translator/)** · **Flowxy-Translator** · MIT License · [@flowxy](https://github.com/floowxy)

*Whisper medium · NLLB-200 1.3B · Edge-TTS · FastAPI · React · PyTorch CUDA*

</div>
