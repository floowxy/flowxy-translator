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

</div>

---

## ¿Qué es esto?

Flowxy-Translator convierte videos de YouTube en material de estudio interactivo. Descarga, transcribe y traduce con GPU, luego te entrega un reproductor con subtítulos en tiempo real o un video MP4 con subtítulos quemados y doblaje en español.

Pensado para **desarrolladores que aprenden inglés técnico** leyendo código mientras escuchan al autor.

---

## Pipeline de procesamiento

```
URL de YouTube
      │
      ▼
┌─────────────┐     yt-dlp        ┌──────────────┐
│   Download  │ ─────────────────▶│  downloads/  │
│  (video o   │   webm / audio    │  {id}_video  │
│   audio)    │                   │  {id}_audio  │
└─────────────┘                   └──────┬───────┘
                                         │
                                         ▼
                                  ┌──────────────┐     float16 FP
                                  │   Whisper    │ ◀── beam=5, VAD
                                  │   medium     │     best_of=5
                                  │   GPU ↔ CPU  │
                                  └──────┬───────┘
                                         │  segmentos con timestamps
                                         ▼
                                  ┌──────────────┐     batch=16
                                  │  NLLB 1.3B   │ ◀── beam=4
                                  │  Transformers│     float16
                                  │   GPU ↔ CPU  │
                                  └──────┬───────┘
                                         │
                  ┌──────────────────────┼──────────────────────┐
                  ▼                      ▼                      ▼
          ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
          │  Reproductor │      │  Video MP4   │      │  Subtítulos  │
          │  en tiempo   │      │  subtítulos  │      │  SRT / VTT   │
          │    real      │      │  + TTS audio │      │  JSON / TXT  │
          └──────────────┘      └──────────────┘      └──────────────┘
```

---

## Gestión de VRAM — Offload automático GPU ↔ CPU

Con 8 GB de VRAM (RTX 4060 Ti), Whisper medium (~1.5 GB) y NLLB 1.3B (~2.6 GB) no caben en GPU al mismo tiempo. El sistema los alterna automáticamente:

```
VRAM (8 GB)
│
│  [Transcripción]              [Traducción]
│  ┌─────────────────┐          ┌─────────────────┐
│  │  Whisper (GPU)  │    →     │  Whisper (CPU)  │
│  │  NLLB    (CPU)  │          │  NLLB    (GPU)  │
│  └─────────────────┘          └─────────────────┘
│         ▲                            ▲
│         └── torch.cuda.empty_cache() cada cambio
```

Ambos modelos viven en RAM (CPU) desde el inicio. Al usar uno, el otro se mueve a CPU y se limpia la caché de CUDA.

---

## Características

| Característica | Detalle |
|---|---|
| **Descarga** | yt-dlp, solo video individual (no playlists), sufijo `_video` / `_audio` para no colisionar |
| **Transcripción** | Whisper medium, VAD filter, beam search 5, FP16 en GPU |
| **Traducción** | NLLB-200 1.3B, batch de 16 segmentos, beam 4, float16 |
| **Reproductor** | Subtítulos en tiempo real, modos original / traducido / bilingüe |
| **Export video** | Subtítulos quemados (FFmpeg), doblaje Edge-TTS opcional |
| **Export texto** | SRT, VTT, JSON, TXT — simple o bilingüe |
| **WebSocket** | Subtítulos en tiempo real para extensión de Chrome |
| **Seguridad** | Path traversal protection, CORS restringido al mismo origen |
| **Cache** | Transcripciones y traducciones en memoria por sesión |
| **Cookies** | `cookies.txt` detectado automáticamente para evitar bloqueos |

---

## Stack técnico completo

<details>
<summary><strong>Backend</strong></summary>

| Paquete | Versión | Rol |
|---|---|---|
| `fastapi` | 0.109.0 | Framework web asíncrono |
| `uvicorn` | 0.27.0 | Servidor ASGI |
| `pydantic` | 2.5.3 | Validación de modelos de datos |
| `websockets` | 12.0 | WebSocket para subtítulos en tiempo real |
| `aiofiles` | 23.2.1 | I/O asíncrono de archivos |
| `python-multipart` | 0.0.6 | Manejo de formularios |

</details>

<details>
<summary><strong>IA y Machine Learning</strong></summary>

| Paquete | Versión | Rol |
|---|---|---|
| `torch` | 2.2.0 | Deep learning, CUDA backend |
| `torchaudio` | 2.2.0 | Procesamiento de audio |
| `openai-whisper` | 20250625 | Transcripción de audio (modelo medium) |
| `transformers` | 4.37.2 | NLLB-200 via HuggingFace |
| `sentencepiece` | 0.1.99 | Tokenización NLLB |

</details>

<details>
<summary><strong>GPU / CUDA (NVIDIA)</strong></summary>

| Paquete | Versión |
|---|---|
| `nvidia-cuda-runtime-cu12` | 12.1.105 |
| `nvidia-cudnn-cu12` | 8.9.2.26 |
| `nvidia-cublas-cu12` | 12.1.3.1 |
| `nvidia-cufft-cu12` | 11.0.2.54 |
| `nvidia-ml-py` | 12.535.133 |

</details>

<details>
<summary><strong>Audio, Video y Utilidades</strong></summary>

| Paquete | Versión | Rol |
|---|---|---|
| `yt-dlp` | 2025.11.12 | Descarga de video (YouTube y otros) |
| `edge-tts` | 7.2.3 | Text-to-Speech Microsoft (doblaje) |
| `av` | 16.0.1 | Procesamiento de video (PyAV) |
| `librosa` | 0.10.1 | Análisis de audio |
| `soundfile` | 0.12.1 | Lectura/escritura de audio |
| `pydub` | 0.25.1 | Manipulación de audio |
| `tqdm` | 4.67.1 | Barras de progreso |
| `pyyaml` | 6.0.3 | Configuración |

</details>

---

## Instalación

### Requisitos

| Componente | Mínimo | Recomendado |
|---|---|---|
| Python | 3.11 | 3.11 |
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
source .venv/bin/activate

# 4. Dependencias Python
pip install --upgrade pip
pip install -r requirements.txt

# 5. Verificar GPU
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 6. Arrancar
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

# 3. Arrancar
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload
```

Luego abre `http://localhost:9000`.

> Los modelos (~4 GB en total) se descargan automáticamente en `models/` la primera vez.

---

## Configuración — `backend/config.py`

```python
# ── Modelos ─────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE = "medium"   # tiny | base | small | medium | large-v2 | large-v3
NLLB_MODEL_SIZE    = "1.3B"     # "600M" | "1.3B"
COMPUTE_TYPE       = "float16"  # float16 | int8_float16 | int8 | float32

# ── GPU ─────────────────────────────────────────────────────────────
DEVICE             = "auto"     # "auto" | "cuda" | "cpu"
BATCH_SIZE         = 8

# ── Whisper ─────────────────────────────────────────────────────────
WHISPER_BEAM_SIZE  = 5
WHISPER_BEST_OF    = 5
WHISPER_VAD_FILTER = True       # Filtro de actividad de voz

# ── NLLB ────────────────────────────────────────────────────────────
NLLB_BEAM_SIZE     = 4
NLLB_BATCH_SIZE    = 16         # Segmentos por batch
NLLB_MAX_LENGTH    = 512

# ── Servidor ────────────────────────────────────────────────────────
SERVER_PORT        = 9000       # Evita conflicto con otros servicios locales
CORS_ORIGINS       = []         # Frontend en mismo origen — no cross-origin
```

### Reducir uso de VRAM (GPU pequeña o CPU)

```python
WHISPER_MODEL_SIZE = "small"     # ~500 MB VRAM
NLLB_MODEL_SIZE    = "600M"      # ~1.2 GB VRAM
COMPUTE_TYPE       = "int8"      # Mínimo uso de memoria
NLLB_BATCH_SIZE    = 8
```

---

## API — Endpoints REST

```
GET  /                           → Frontend (index.html)
GET  /player                     → Reproductor con subtítulos
GET  /health                     → Health check
GET  /api/gpu-stats              → Estado de la GPU (VRAM, CUDA info)

POST /api/download               → Descarga video/audio de YouTube
POST /api/transcribe             → Transcribe con Whisper
POST /api/translate              → Traduce texto suelto
POST /api/translate-transcript   → Traduce transcripción completa por segmentos
POST /api/export                 → Exporta SRT / VTT / JSON / TXT
POST /api/export-video           → Exporta MP4 con subtítulos ± TTS

GET  /api/subtitles/{file}       → Segmentos con timestamps para el player
GET  /api/export/{file}          → Descarga archivo exportado
GET  /audio/{file}               → Sirve audio descargado
GET  /video/{file}               → Sirve video descargado (webm)

WS   /ws                         → WebSocket tiempo real (extensión Chrome)
```

---

## Uso paso a paso

**1 · Descargar**
- Pega la URL de YouTube
- Activa "Descargar VIDEO COMPLETO" (necesario para el reproductor)
- El sistema ignora playlists automáticamente y guarda el archivo con sufijo `_video`

**2 · Transcribir**
- Selecciona idioma o deja en auto-detect
- Whisper aplica VAD para ignorar silencios antes de transcribir
- El resultado se guarda en caché en memoria

**3 · Traducir**
- Selecciona idioma destino (español por defecto)
- Los segmentos se traducen en batches de 16 — mucho más rápido que uno a uno
- La traducción también queda en caché

**4 · Reproducir**
- Abre el reproductor integrado
- Cambia entre modo original, traducido o bilingüe en vivo

**5 · Exportar**
- **Video MP4** con subtítulos quemados (FFmpeg, ~30 s)
- **Video MP4** con subtítulos + doblaje Edge-TTS (~2–3 min)
- **SRT / VTT** para usar en cualquier reproductor
- **JSON / TXT** con toda la transcripción y traducción

---

## Rendimiento

### RTX 4060 Ti 8 GB + Ryzen 5 7600X + 32 GB RAM

| Tarea | Tiempo |
|---|---|
| Transcripción (medium, 10 min de video) | ~50–100 s |
| Traducción (1.3B, 10 min, batch 16) | ~20–40 s |
| Export video solo subtítulos | ~30 s |
| Export video + TTS | ~2–3 min |
| **Total para video de 10 min** | **~3–5 min** |

### Solo CPU (i7 / Ryzen 7)

| Tarea | Tiempo |
|---|---|
| Transcripción (medium, 10 min de video) | ~5–10 min |
| Traducción (1.3B, 10 min) | ~3–6 min |
| Export video solo subtítulos | ~2–3 min |
| **Total para video de 10 min** | **~12–20 min** |

---

## Estructura del proyecto

```
flowxy-translator/
│
├── backend/
│   ├── config.py                  # Configuración central + helpers GPU
│   ├── main.py                    # App FastAPI, endpoints, WebSocket
│   │
│   ├── whisper/
│   │   ├── whisper_engine.py      # Carga/offload, transcribe_file, transcribe_array
│   │   └── whisper_utils.py
│   │
│   ├── translation/
│   │   ├── nllb_engine.py         # Carga/offload, translate_text, translate_batch, translate_segments
│   │   ├── translation_utils.py
│   │   └── language_detect.py
│   │
│   ├── export/
│   │   ├── srt_exporter.py        # SRT simple y bilingüe
│   │   ├── vtt_exporter.py        # VTT simple y bilingüe
│   │   ├── transcript_export.py   # JSON / TXT / TXT bilingüe
│   │   └── video_export.py        # FFmpeg subtítulos + Edge-TTS
│   │
│   ├── websocket/
│   │   ├── realtime_handler.py    # Lógica WebSocket (extensión Chrome)
│   │   ├── ws_protocol.py
│   │   └── ws_server.py
│   │
│   └── utils/
│       ├── gpu_stats.py           # VRAM, CUDA info
│       ├── logger.py
│       ├── timers.py
│       └── chunker.py
│
├── frontend/
│   ├── index.html                 # UI principal (glassmorphism)
│   ├── player.html                # Reproductor con subtítulos en tiempo real
│   ├── app.js                     # Lógica y llamadas a la API
│   ├── video_player.js            # Player + sincronización de subtítulos
│   └── styles.css
│
├── downloads/                     # Videos/audios descargados
├── exports/                       # MP4, SRT, VTT, JSON exportados
├── models/
│   ├── whisper/                   # Modelo Whisper descargado automáticamente
│   └── nllb/                      # Modelo NLLB descargado automáticamente
│
├── cookies.txt                    # (Opcional) Cookies del navegador para yt-dlp
├── requirements.txt
└── LICENSE
```

---

## Seguridad

- **Path traversal**: `_safe_filename()` valida cada nombre de archivo recibido por la API — rechaza `../`, rutas absolutas y caracteres peligrosos antes de acceder al disco
- **CORS**: `CORS_ORIGINS = []` — el frontend se sirve desde el mismo origen que la API (FastAPI static files), por lo que no hay acceso cross-origin
- **Cookies**: `cookies.txt` solo se lee localmente por yt-dlp; nunca se expone ni se transmite por ningún endpoint
- **Input validation**: todos los modelos de request usan Pydantic v2 con tipos estrictos

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

</details>

<details>
<summary><strong>YouTube bloquea la descarga</strong></summary>

Exporta las cookies de tu navegador a un archivo `cookies.txt` en la raíz del proyecto. El servidor lo detecta automáticamente en cada descarga.

</details>

<details>
<summary><strong>Video no se reproduce en el player</strong></summary>

El reproductor necesita el archivo de **video completo** (no solo audio). Asegúrate de haber marcado "Descargar VIDEO COMPLETO" al descargar. Si tienes solo audio, vuelve a descargar con esa opción activa.

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
<summary><strong>Dependencias rotas en Windows (Visual C++)</strong></summary>

Instala [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) y vuelve a ejecutar `pip install -r requirements.txt`.

</details>

<details>
<summary><strong>Primera ejecución muy lenta</strong></summary>

Los modelos se descargan una sola vez:
- Whisper medium → ~1.5 GB en `models/whisper/`
- NLLB 1.3B → ~2.6 GB en `models/nllb/`

Las siguientes ejecuciones cargan los modelos directamente desde disco.

</details>

---

## ¿La traducción es literal?

No. NLLB-200 traduce por **contexto y significado**:

```
Original:  "I'm gonna grab a bite before we dive into the code"
Literal:   "Voy a agarrar un mordisco antes de que nos sumerjamos en el código"
NLLB:      "Voy a comer algo antes de meternos con el código"
```

El modelo reorganiza frases, adapta expresiones idiomáticas y mantiene el tono técnico del contenido.

---

<div align="center">

**Flowxy-Translator** · MIT License · [@flowxy](https://github.com/floowxy)

*Whisper medium · NLLB-200 1.3B · Edge-TTS · FastAPI · PyTorch CUDA*

</div>
