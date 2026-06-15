# Flowxy-Translator

Sistema de transcripción y traducción de videos con GPU usando Whisper v3 y NLLB-200.

## 🎯 Propósito

Herramienta diseñada para **aprender inglés técnico de programación** mediante videos de YouTube. Permite:

- 📚 **Estudiar contenido técnico** en inglés con traducción al español
- 🎓 **Aprender vocabulario** de programación en contexto
- 🔄 **Comparar** inglés original con traducción inteligente
- 💾 **Generar videos** con subtítulos permanentes para estudio offline

Ideal para desarrolladores que quieren mejorar su inglés técnico viendo tutoriales, conferencias y documentación.

## ✨ Características

- ✅ **Descarga de videos** de YouTube con yt-dlp
- ✅ **Transcripción automática** con Whisper v3 (GPU)
- ✅ **Traducción** a múltiples idiomas con NLLB-200 (GPU)
- ✅ **Reproductor en tiempo real** con subtítulos sincronizados
- ✅ **Exportación de video** con subtítulos quemados en español
- ✅ **Audio TTS opcional** con Edge-TTS (doblaje completo)

## 🚀 Instalación

### Requisitos del Sistema

#### Software Base

- **Python**: 3.11 o 3.12 (recomendado 3.11.9)
- **CUDA Toolkit**: 12.1 o superior (para aceleración GPU)
- **FFmpeg**: 6.0+ con soporte H.264
- **Git**: Para clonar el repositorio

#### Hardware Recomendado

> ⚠️ **Importante**: El sistema **funciona con o sin GPU NVIDIA**. La GPU solo acelera el proceso, pero no es obligatoria.

**Con GPU NVIDIA (Recomendado para velocidad):**

- **GPU**: NVIDIA RTX 4060 Ti (8GB VRAM) o superior
  - Mínimo: GTX 1660 (6GB VRAM)
  - Óptimo: RTX 4060 Ti / RTX 3060 (8GB+)
- **Velocidad**: Transcripción ~5-10s por minuto de audio

**Sin GPU (Solo CPU - Funcional pero más lento):**

- **CPU**: Cualquier procesador moderno (i5/Ryzen 5 o superior)
- **Velocidad**: Transcripción ~30-60s por minuto de audio
- **Nota**: El sistema detecta automáticamente si no hay GPU y usa CPU

**Común para ambos:**

- **RAM**: 16GB mínimo, 32GB recomendado
- **Almacenamiento**: 20GB libres (modelos + videos)

#### Instalación de Dependencias del Sistema

> 📝 **Nota**: CUDA Toolkit solo es necesario si tienes GPU NVIDIA y quieres aceleración. Sin CUDA, el sistema funciona en CPU.

**Windows:**

```powershell
# 1. Instalar Python 3.11 desde python.org
# 2. (Opcional) Instalar CUDA Toolkit 12.1+ desde nvidia.com/cuda-downloads
# 3. Instalar FFmpeg:
winget install FFmpeg
# O descargar desde: https://www.gyan.dev/ffmpeg/builds/
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv ffmpeg git
# (Opcional) CUDA: Seguir guía oficial de NVIDIA si tienes GPU NVIDIA
```

**macOS:**

```bash
brew install python@3.11 ffmpeg git
# Nota: Sin soporte GPU (solo CPU)
```

> **⚠️ Nota importante**: Los modelos de IA (Whisper, NLLB) **NO están incluidos** en este repositorio. Se descargarán automáticamente la primera vez que ejecutes el sistema (~8GB).

### Pasos de Instalación

#### 1. Clonar Repositorio

**Windows (PowerShell):**

```powershell
git clone <repo-url>
cd flowxy-translator
```

**Linux/macOS:**

```bash
git clone <repo-url>
cd flowxy-translator
```

#### 2. Crear Entorno Virtual

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux/macOS:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

#### 3. Instalar Dependencias Python

**Todos los sistemas (con entorno virtual activado):**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> ⏱️ **Tiempo estimado**: 5-10 minutos (depende de tu conexión)

#### 4. Verificar Instalación GPU (Opcional)

**Todos los sistemas:**

```bash
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

#### 5. Ejecutar Servidor

**Windows (PowerShell/CMD):**

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload
```

**Linux/macOS:**

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload
```

#### 6. Abrir en Navegador

**Todos los sistemas:**

```text
http://localhost:9000
```

## ⚡ Inicio Rápido (Uso Diario)

Una vez instalado, estos son los comandos que usarás regularmente:

### Windows (PowerShell)

```powershell
# 1. Navegar al proyecto
cd flowxy-translator

# 2. Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# 3. Iniciar servidor
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload

# 4. Abrir navegador en http://localhost:9000
```

### Linux/macOS

```bash
# 1. Navegar al proyecto
cd flowxy-translator

# 2. Activar entorno virtual
source .venv/bin/activate

# 3. Iniciar servidor
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload

# 4. Abrir navegador en http://localhost:9000
```

### Comandos Útiles

**Actualizar dependencias:**

```bash
pip install --upgrade -r requirements.txt
```

**Verificar estado GPU:**

```bash
python backend/config.py
```

**Limpiar descargas y exportaciones:**

```bash
# Windows
rmdir /s /q downloads exports
mkdir downloads exports

# Linux/macOS
rm -rf downloads/* exports/*
```

**Detener servidor:**

```text
Ctrl + C (en la terminal donde corre uvicorn)
```

## 📖 Uso

### 1. Descargar Video

- Pega URL de YouTube
- Marca "Descargar VIDEO COMPLETO"
- Click "DESCARGAR VIDEO"

### 2. Transcribir

- Click "TRANSCRIBIR AUDIO"
- Auto-detecta idioma o selecciona manualmente

### 3. Traducir

- Selecciona idioma destino (español por defecto)
- Click "TRADUCIR A ESPAÑOL"

### 4. Ver con Subtítulos en Tiempo Real

- Click "🎬 ABRIR REPRODUCTOR CON SUBTÍTULOS EN TIEMPO REAL"
- Selecciona modo: Original / Traducido / Bilingüe

### 5. Generar Video Final

- **Opción A**: Solo subtítulos (~30s)
  - NO marcar checkbox TTS
  - Click "GENERAR VIDEO CON SUBTÍTULOS EN ESPAÑOL"
  
- **Opción B**: Subtítulos + TTS (~2-3min)
  - Marcar "Incluir audio TTS en español"
  - Click "GENERAR VIDEO CON SUBTÍTULOS EN ESPAÑOL"

## 🛠️ Tecnologías

- **Backend**: FastAPI + Python
- **Transcripción**: OpenAI Whisper v3
- **Traducción**: Meta NLLB-200 (CTranslate2)
- **TTS**: Microsoft Edge-TTS
- **Video**: FFmpeg
- **Descarga**: yt-dlp
- **GPU**: CUDA + PyTorch

## � Dependencias Python

### Core Framework

- **fastapi** (0.109.0) - Framework web asíncrono
- **uvicorn** (0.27.0) - Servidor ASGI
- **pydantic** (2.5.3) - Validación de datos
- **websockets** (12.0) - Comunicación en tiempo real

### IA y Machine Learning

- **torch** (2.2.0) - Framework de deep learning con CUDA
- **torchaudio** (2.2.0) - Procesamiento de audio
- **transformers** (4.37.2) - Modelos de HuggingFace
- **openai-whisper** (20250625) - Transcripción de audio
- **ctranslate2** (4.0.0) - Motor de traducción optimizado
- **sentencepiece** (0.1.99) - Tokenización para NLLB

### Procesamiento de Audio

- **librosa** (0.10.1) - Análisis de audio
- **soundfile** (0.12.1) - Lectura/escritura de archivos de audio
- **pydub** (0.25.1) - Manipulación de audio
- **audioread** (3.1.0) - Decodificación de formatos de audio

### Video y Multimedia

- **yt-dlp** (2025.11.12) - Descarga de videos de YouTube
- **av** (16.0.1) - Procesamiento de video (PyAV)
- **edge-tts** (7.2.3) - Text-to-Speech de Microsoft

### GPU y CUDA (NVIDIA)

- **nvidia-cuda-runtime-cu12** (12.1.105)
- **nvidia-cudnn-cu12** (8.9.2.26)
- **nvidia-cublas-cu12** (12.1.3.1)
- **nvidia-cufft-cu12** (11.0.2.54)
- **nvidia-ml-py** (12.535.133) - Monitoreo de GPU

### Utilidades

- **aiofiles** (23.2.1) - I/O asíncrono de archivos
- **python-multipart** (0.0.6) - Manejo de formularios
- **requests** (2.32.5) - Cliente HTTP
- **tqdm** (4.67.1) - Barras de progreso
- **pyyaml** (6.0.3) - Configuración YAML

### Desarrollo y Testing

- **pytest** (7.4.4) - Framework de testing
- **python-dotenv** (1.0.1) - Variables de entorno

> 📝 **Nota**: El archivo `requirements.txt` contiene todas las dependencias con versiones exactas para garantizar compatibilidad.

## �📁 Estructura

```text
flowxy-translator/
├── backend/
│   ├── export/          # Exportadores (SRT, VTT, video)
│   ├── translation/     # Motor NLLB
│   ├── whisper/         # Motor Whisper
│   ├── utils/           # Utilidades
│   └── main.py          # API FastAPI
├── frontend/
│   ├── index.html       # UI principal
│   ├── player.html      # Reproductor
│   ├── app.js           # Lógica frontend
│   ├── video_player.js  # Player con subtítulos
│   └── styles.css       # Estilos
├── downloads/           # Videos descargados
├── exports/             # Videos exportados
└── requirements.txt     # Dependencias Python
```

## ⚙️ Configuración

Edita `backend/config.py`:

```python
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9000
WHISPER_MODEL_SIZE = "base"  # tiny, base, small, medium, large-v2, large-v3
NLLB_MODEL_SIZE = "1.3B"     # "600M" o "1.3B"
```

## 🎨 Características del Video Exportado

- **Formato**: MP4 (H.264)
- **Subtítulos**: Quemados permanentemente
- **Fuente**: Arial, tamaño 18
- **Color**: Blanco con borde negro
- **Posición**: Abajo centro
- **Audio TTS**: Voz natural en español (Microsoft)

## 📊 Rendimiento

### Con GPU NVIDIA (RTX 4060 Ti 8GB)

| Tarea | Tiempo aproximado |
|-------|-------------------|
| Transcripción | ~5-10s por minuto de audio |
| Traducción | ~10-30s (primera vez carga modelo) |
| Video con subtítulos | ~30s |
| Video con TTS | ~2-3min |

**Ejemplo**: Video de 10 minutos → Proceso completo en ~3-5 minutos

### Sin GPU (Solo CPU - Intel i7 / Ryzen 7)

| Tarea | Tiempo aproximado |
|-------|-------------------|
| Transcripción | ~30-60s por minuto de audio |
| Traducción | ~2-5min (primera vez carga modelo) |
| Video con subtítulos | ~2-3min |
| Video con TTS | ~5-8min |

**Ejemplo**: Video de 10 minutos → Proceso completo en ~15-25 minutos

> 💡 **Tip**: Si no tienes GPU NVIDIA, puedes usar modelos más pequeños para mejorar la velocidad (ver sección de Solución de Problemas #9)

## 🐛 Solución de Problemas

### Problemas Comunes

#### 1. Error al activar entorno virtual (Windows)

**Problema**: `cannot be loaded because running scripts is disabled`

**Solución (PowerShell como Administrador):**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. CUDA no detectado

**Verificar instalación:**

```bash
# Windows (PowerShell)
nvidia-smi

# Verificar en Python
python -c "import torch; print(torch.cuda.is_available())"
```

**Solución:**

- Reinstalar CUDA Toolkit 12.1+
- Verificar drivers NVIDIA actualizados
- Reinstalar PyTorch: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`

#### 3. FFmpeg no encontrado

**Windows:**

```powershell
# Verificar instalación
ffmpeg -version

# Si no está instalado:
winget install FFmpeg
# O agregar FFmpeg al PATH manualmente
```

**Linux:**

```bash
sudo apt install ffmpeg
```

#### 4. Video no se reproduce

- ✅ Asegúrate de marcar "Descargar VIDEO COMPLETO"
- ✅ Borra el archivo viejo en `/downloads` y descarga de nuevo
- ✅ Verifica que FFmpeg esté instalado correctamente

#### 5. Error de traducción / Modelo no carga

- ⏱️ Primera vez tarda 1-2 minutos (descarga modelo NLLB ~2GB)
- 💾 Verifica espacio en disco (mínimo 10GB libres)
- 🎮 Verifica VRAM disponible (mínimo 6GB)

**Limpiar caché de modelos:**

```bash
# Windows
rmdir /s /q models
mkdir models

# Linux/macOS
rm -rf models/
mkdir models
```

#### 6. Subtítulos no aparecen en reproductor

- 🔄 Recarga la página (F5)
- ✅ Verifica que transcripción esté completa (100%)
- ✅ Verifica que traducción esté completa (100%)
- 🔍 Revisa la consola del navegador (F12) para errores

#### 7. Error "Port 9000 already in use"

**Windows:**

```powershell
# Ver qué proceso usa el puerto
netstat -ano | findstr :9000

# Matar proceso (reemplazar PID)
taskkill /PID <PID> /F
```

**Linux/macOS:**

```bash
# Ver proceso
lsof -i :9000

# Matar proceso
kill -9 <PID>
```

#### 8. Instalación de dependencias falla

**Error común**: `Microsoft Visual C++ 14.0 or greater is required` (Windows)

**Solución:**

- Instalar [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- O instalar Visual Studio Community con "Desktop development with C++"

#### 9. Memoria GPU insuficiente

**Reducir uso de VRAM** editando `backend/config.py`:

```python
WHISPER_MODEL_SIZE = "tiny"  # En vez de "base"
NLLB_MODEL_SIZE = "600M"     # En vez de "1.3B"
COMPUTE_TYPE = "int8"        # En vez de "float16"
```

#### 10. Rendimiento lento en CPU

Si no tienes GPU NVIDIA, el sistema funcionará en CPU pero será más lento:

- Transcripción: ~30-60s por minuto de audio
- Traducción: ~2-5 minutos
- Considera usar modelos más pequeños (ver punto 9)

### Logs y Diagnóstico

**Ver logs del servidor:**

```bash
# El servidor muestra logs en tiempo real en la terminal
# Para guardar logs:
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --log-level debug > server.log 2>&1
```

**Verificar configuración:**

```bash
python backend/config.py
```

### ¿La traducción es literal?

**No, la traducción NO es literal**. El sistema usa NLLB-200, un modelo de IA que traduce por **contexto y significado**, no palabra por palabra.

**Cómo funciona**:

- ✅ Traduce el **sentido** de la frase, no literalmente
- ✅ Adapta expresiones idiomáticas
- ✅ Mantiene el tono y contexto
- ✅ Puede reorganizar palabras para que suene natural en español

**Ejemplo**:

- Original: "I'm gonna grab a bite"
- Literal: ❌ "Voy a agarrar un mordisco"
- NLLB: ✅ "Voy a comer algo"

Es una **traducción inteligente** que prioriza que suene natural en el idioma destino.

## 📝 Licencia

MIT

## 👤 Autor

flowxy

---

Powered by Whisper v3 + NLLB-200 + Edge-TTS
