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

### Requisitos

- Python 3.11+
- CUDA 12.1+ (para GPU)
- FFmpeg
- NVIDIA GPU (recomendado: RTX 4060 Ti o superior)

### Pasos

1. **Clonar repositorio**

```bash
git clone <repo-url>
cd flowxy-translator
```

1. **Crear entorno virtual**

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
```

1. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

1. **Ejecutar servidor**

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload
```

1. **Abrir en navegador**

```text
http://localhost:9000
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

## 📁 Estructura

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
WHISPER_MODEL = "base"  # tiny, base, small, medium, large
NLLB_MODEL = "nllb-200-distilled-600M"
```

## 🎨 Características del Video Exportado

- **Formato**: MP4 (H.264)
- **Subtítulos**: Quemados permanentemente
- **Fuente**: Arial, tamaño 18
- **Color**: Blanco con borde negro
- **Posición**: Abajo centro
- **Audio TTS**: Voz natural en español (Microsoft)

## 📊 Rendimiento

Con RTX 4060 Ti (8GB):

- Transcripción: ~5-10s por minuto de audio
- Traducción: ~10-30s (primera vez carga modelo)
- Video con subtítulos: ~30s
- Video con TTS: ~2-3min

## 🐛 Solución de Problemas

### Video no se reproduce

- Asegúrate de marcar "Descargar VIDEO COMPLETO"
- Borra el archivo viejo y descarga de nuevo

### Error de traducción

- Primera vez tarda en cargar modelo NLLB (~1-2GB)
- Verifica que tengas suficiente VRAM

### Subtítulos no aparecen

- Recarga la página
- Verifica que transcripción y traducción estén completas

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
