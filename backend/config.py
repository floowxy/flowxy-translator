"""
Configuración central para Flowxy-Translator
GPU: RTX 4060 Ti 8GB
CPU: Ryzen 5 7600X
RAM: 32GB
"""
import os
from pathlib import Path
from typing import Literal

# ============================================
# RUTAS BASE
# ============================================
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
MODELS_DIR = BASE_DIR / "models"
DOWNLOADS_DIR = BASE_DIR / "downloads"
EXPORTS_DIR = BASE_DIR / "exports"

# Crear directorios necesarios
MODELS_DIR.mkdir(exist_ok=True, parents=True)
DOWNLOADS_DIR.mkdir(exist_ok=True, parents=True)
EXPORTS_DIR.mkdir(exist_ok=True, parents=True)

# ============================================
# CONFIGURACIÓN GPU
# ============================================
# Device: "cuda", "cpu", "auto"
DEVICE: Literal["cuda", "cpu", "auto"] = "auto"

# Compute type para CTranslate2
# RTX 4060 Ti soporta: float16, int8_float16, int8
COMPUTE_TYPE: Literal["float16", "int8_float16", "int8", "float32"] = "float16"

# Número de workers GPU (1-2 para RTX 4060 Ti)
GPU_NUM_WORKERS = 1

# Tamaño de batch para inferencia
BATCH_SIZE = 8

# ============================================
# WHISPER CONFIGURACIÓN
# ============================================
WHISPER_MODEL_DIR = MODELS_DIR / "whisper"
WHISPER_MODEL_DIR.mkdir(exist_ok=True, parents=True)

# Modelo: "tiny", "base", "small", "medium", "large-v2", "large-v3"
# Para GPU RTX 4060 Ti: base es más rápido y usa menos memoria
WHISPER_MODEL_SIZE = "base"

# Parámetros de transcripción
WHISPER_BEAM_SIZE = 5
WHISPER_BEST_OF = 5
WHISPER_TEMPERATURE = 0.0

# VAD (Voice Activity Detection)
WHISPER_VAD_FILTER = True
WHISPER_VAD_PARAMS = {
    "threshold": 0.5,
    "min_speech_duration_ms": 250,
    "min_silence_duration_ms": 500,
    "speech_pad_ms": 400,
}

# Language
WHISPER_LANGUAGE = None  # Auto-detect
WHISPER_TASK = "transcribe"  # o "translate" para traducir a inglés

# ============================================
# NLLB CONFIGURACIÓN (Traducción)
# ============================================
NLLB_MODEL_DIR = MODELS_DIR / "nllb"
NLLB_MODEL_DIR.mkdir(exist_ok=True, parents=True)

# Modelo NLLB: "600M" o "1.3B"
# Para RTX 4060 Ti 8GB: 1.3B funciona bien con float16
NLLB_MODEL_SIZE = "1.3B"

# HuggingFace model name
NLLB_MODEL_NAME = (
    "facebook/nllb-200-distilled-600M" 
    if NLLB_MODEL_SIZE == "600M" 
    else "facebook/nllb-200-1.3B"
)

# Parámetros de traducción
NLLB_BEAM_SIZE = 4
NLLB_MAX_LENGTH = 512
NLLB_BATCH_SIZE = 16

# Códigos de idioma NLLB más comunes
NLLB_LANG_CODES = {
    "es": "spa_Latn",  # Español
    "en": "eng_Latn",  # Inglés
    "fr": "fra_Latn",  # Francés
    "de": "deu_Latn",  # Alemán
    "it": "ita_Latn",  # Italiano
    "pt": "por_Latn",  # Portugués
    "ru": "rus_Cyrl",  # Ruso
    "ja": "jpn_Jpan",  # Japonés
    "zh": "zho_Hans",  # Chino simplificado
    "ko": "kor_Hang",  # Coreano
    "ar": "arb_Arab",  # Árabe
    "hi": "hin_Deva",  # Hindi
}

# ============================================
# TTS CONFIGURACIÓN (Opcional)
# ============================================
TTS_MODEL_DIR = MODELS_DIR / "xtts"
TTS_MODEL_DIR.mkdir(exist_ok=True, parents=True)

TTS_ENABLED = False  # Activar cuando sea necesario
TTS_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
TTS_LANGUAGE = "es"  # Default a español
TTS_SPEAKER_WAV = None  # Path a audio de referencia

# ============================================
# AUDIO PROCESAMIENTO
# ============================================
AUDIO_SAMPLE_RATE = 16000  # Whisper requiere 16kHz
AUDIO_CHANNELS = 1  # Mono
AUDIO_CHUNK_LENGTH_S = 30  # Segundos por chunk

# ============================================
# SERVIDOR
# ============================================
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9000  # Cambiado de 8000 para no interferir con Overleaf
SERVER_RELOAD = True  # Solo en desarrollo

# CORS
CORS_ORIGINS = ["*"]  # En producción: lista específica

# ============================================
# LOGGING
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = BASE_DIR / "flowxy-translator.log"

# ============================================
# EXPORT
# ============================================
EXPORT_FORMATS = ["srt", "vtt", "txt", "json"]
SRT_MAX_CHARS_PER_LINE = 42
SRT_MAX_LINES = 2

# ============================================
# FUNCIONES HELPER
# ============================================
def get_device() -> str:
    """Detecta el device disponible"""
    if DEVICE == "auto":
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"
    return DEVICE


def validate_gpu() -> dict:
    """Valida que GPU esté disponible y retorna info"""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        
        if cuda_available:
            return {
                "available": True,
                "device_name": torch.cuda.get_device_name(0),
                "device_count": torch.cuda.device_count(),
                "cuda_version": torch.version.cuda,
                "memory_allocated": torch.cuda.memory_allocated(0),
                "memory_reserved": torch.cuda.memory_reserved(0),
            }
        else:
            return {
                "available": False,
                "message": "CUDA no disponible. Usando CPU."
            }
    except ImportError:
        return {
            "available": False,
            "message": "PyTorch no instalado."
        }


# ============================================
# VALIDACIÓN AL IMPORTAR
# ============================================
if __name__ == "__main__":
    import json
    print("=" * 50)
    print("FLOWXY-TRANSLATOR - Configuración")
    print("=" * 50)
    print(f"Device seleccionado: {get_device()}")
    print(f"Compute type: {COMPUTE_TYPE}")
    print(f"Whisper model: {WHISPER_MODEL_SIZE}")
    print(f"NLLB model: {NLLB_MODEL_SIZE}")
    print("\nGPU Info:")
    print(json.dumps(validate_gpu(), indent=2))
