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

# ============================================
# WHISPER CONFIGURACIÓN
# ============================================
WHISPER_MODEL_DIR = MODELS_DIR / "whisper"
WHISPER_MODEL_DIR.mkdir(exist_ok=True, parents=True)

# Modelo: "tiny", "base", "small", "medium", "large-v2", "large-v3"
# "medium" (~5GB VRAM) + NLLB 1.3B (~2.6GB) caben en una RTX 4060 Ti 8GB
WHISPER_MODEL_SIZE = "medium"

# Parámetros de transcripción
WHISPER_BEAM_SIZE = 5
WHISPER_BEST_OF = 5
WHISPER_TEMPERATURE = 0.0

# Filtrado de segmentos sin voz (parámetros nativos de openai-whisper)
# WHISPER_VAD_FILTER existía antes pero es un param de faster-whisper, no de openai-whisper.
# Los equivalentes correctos son estos dos:
WHISPER_NO_SPEECH_THRESHOLD = 0.6       # descarta segmentos con < 60% prob de habla
WHISPER_COMPRESSION_RATIO_THRESHOLD = 2.4  # descarta segmentos comprimidos (garbage)

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

# Parámetros de traducción
NLLB_BEAM_SIZE = 5           # +1 beam mejora calidad notablemente (~20% más lento)
NLLB_MAX_LENGTH = 512
NLLB_BATCH_SIZE = 16
NLLB_REPETITION_PENALTY = 1.1   # penaliza frases repetidas
NLLB_NO_REPEAT_NGRAM = 4        # evita repetir bloques de 4 palabras exactas
NLLB_CONTEXT_AWARE = True        # usar el segmento anterior como contexto

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
# PRESET / config.local.json — override por hardware
# ============================================
# Si el usuario guardó un preset desde el frontend (Configuración), estas 9
# variables se sobreescriben aquí. Sin config.local.json, se auto-detecta un
# preset por la VRAM real de la máquina (ver backend/presets.py) — no se
# persiste nada hasta que el usuario guarde explícitamente.
from backend.presets import resolve_effective_config

_model_defaults = {
    "WHISPER_MODEL_SIZE": WHISPER_MODEL_SIZE,
    "WHISPER_BEAM_SIZE": WHISPER_BEAM_SIZE,
    "WHISPER_BEST_OF": WHISPER_BEST_OF,
    "NLLB_MODEL_SIZE": NLLB_MODEL_SIZE,
    "NLLB_BEAM_SIZE": NLLB_BEAM_SIZE,
    "NLLB_BATCH_SIZE": NLLB_BATCH_SIZE,
    "NLLB_REPETITION_PENALTY": NLLB_REPETITION_PENALTY,
    "NLLB_NO_REPEAT_NGRAM": NLLB_NO_REPEAT_NGRAM,
    "NLLB_CONTEXT_AWARE": NLLB_CONTEXT_AWARE,
}
_effective, ACTIVE_PRESET, ACTIVE_OVERRIDES = resolve_effective_config(BASE_DIR, _model_defaults)

WHISPER_MODEL_SIZE = _effective["WHISPER_MODEL_SIZE"]
WHISPER_BEAM_SIZE = _effective["WHISPER_BEAM_SIZE"]
WHISPER_BEST_OF = _effective["WHISPER_BEST_OF"]
NLLB_MODEL_SIZE = _effective["NLLB_MODEL_SIZE"]
NLLB_BEAM_SIZE = _effective["NLLB_BEAM_SIZE"]
NLLB_BATCH_SIZE = _effective["NLLB_BATCH_SIZE"]
NLLB_REPETITION_PENALTY = _effective["NLLB_REPETITION_PENALTY"]
NLLB_NO_REPEAT_NGRAM = _effective["NLLB_NO_REPEAT_NGRAM"]
NLLB_CONTEXT_AWARE = _effective["NLLB_CONTEXT_AWARE"]

# Depende de NLLB_MODEL_SIZE — se calcula DESPUÉS del override
NLLB_MODEL_NAME = (
    "facebook/nllb-200-distilled-600M"
    if NLLB_MODEL_SIZE == "600M"
    else "facebook/nllb-200-1.3B"
)

# ============================================
# SERVIDOR
# ============================================
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9000  # Cambiado de 8000 para no interferir con Overleaf
SERVER_RELOAD = True  # Solo en desarrollo

# CORS
# El frontend se sirve desde el mismo origen (FastAPI), por lo que no se
# necesita acceso cross-origin. Se deja vacío por seguridad, ya que
# SERVER_HOST="0.0.0.0" expone el servidor a la red local.
CORS_ORIGINS = []

# ============================================
# LOGGING
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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
    print(f"Whisper model: {WHISPER_MODEL_SIZE}")
    print(f"NLLB model: {NLLB_MODEL_SIZE}")
    print("\nGPU Info:")
    print(json.dumps(validate_gpu(), indent=2))
