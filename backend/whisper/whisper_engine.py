"""
Whisper Engine - Motor de transcripción GPU-optimizado con OpenAI Whisper
Optimizado para RTX 4060 Ti usando PyTorch + CUDA
"""
import logging
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, List, Optional
import torch
import whisper

from backend.config import (
    WHISPER_MODEL_DIR,
    WHISPER_MODEL_SIZE,
    WHISPER_LANGUAGE,
    WHISPER_TASK,
    get_device,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_whisper_model():
    """
    Obtiene o carga el modelo Whisper (cached)
    
    Returns:
        Modelo Whisper de OpenAI
    """
    try:
        device = get_device()
        logger.info(f"Cargando Whisper {WHISPER_MODEL_SIZE} en {device}")
        
        # Crear directorio de modelos si no existe
        WHISPER_MODEL_DIR.mkdir(exist_ok=True, parents=True)
        
        # Cargar modelo
        model = whisper.load_model(
            WHISPER_MODEL_SIZE,
            device=device,
            download_root=str(WHISPER_MODEL_DIR),
        )
        
        logger.info(f"✓ Modelo Whisper cargado: {WHISPER_MODEL_SIZE}")
        logger.info(f"✓ Device: {device}")
        
        return model
        
    except Exception as e:
        logger.error(f"Error cargando modelo Whisper: {e}")
        raise


def transcribe_file(
    audio_path: Path,
    language: Optional[str] = None,
    task: str = "transcribe",
    **kwargs
) -> Dict[str, Any]:
    """
    Transcribe un archivo de audio completo
    
    Args:
        audio_path: Path al archivo de audio
        language: Código de idioma (ej: "en", "es") o None para auto-detect
        task: "transcribe" o "translate" (traducir a inglés)
        
    Returns:
        Dict con resultado:
        {
            "status": "ok",
            "text": "transcripción completa",
            "segments": [{"start": 0.0, "end": 1.5, "text": "..."}],
            "language": "en",
            "duration": 123.45
        }
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Archivo no existe: {audio_path}")
    
    # Valores por defecto
    if language is None:
        language = WHISPER_LANGUAGE
    
    logger.info(f"Transcribiendo: {audio_path.name}")
    logger.info(f"  Language: {language or 'auto-detect'}")
    logger.info(f"  Task: {task}")
    
    try:
        model = get_whisper_model()
        
        # Transcribir con configuración optimizada para GPU
        result = model.transcribe(
            str(audio_path),
            language=language,
            task=task,
            verbose=False,
            fp16=torch.cuda.is_available(),  # Usar FP16 en GPU
        )
        
        # Procesar segmentos
        segments: List[Dict[str, Any]] = []
        
        for seg in result.get("segments", []):
            segment_dict = {
                "id": seg.get("id", 0),
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "text": seg.get("text", "").strip(),
            }
            segments.append(segment_dict)
        
        # Texto completo
        full_text = result.get("text", "").strip()
        detected_language = result.get("language", language or "unknown")
        
        logger.info(f"✓ Transcripción completada")
        logger.info(f"  Idioma detectado: {detected_language}")
        logger.info(f"  Segmentos: {len(segments)}")
        logger.info(f"  Caracteres: {len(full_text)}")
        
        return {
            "status": "ok",
            "text": full_text,
            "segments": segments,
            "language": detected_language,
            "duration": round(segments[-1]["end"], 2) if segments else 0.0,
        }
        
    except Exception as e:
        logger.error(f"Error en transcripción: {e}")
        raise


def transcribe_array(
    audio_array,
    sample_rate: int = 16000,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribe un array de audio numpy
    
    Args:
        audio_array: Array numpy con audio
        sample_rate: Sample rate del audio
        language: Código de idioma
        
    Returns:
        Dict con resultado de transcripción
    """
    try:
        import numpy as np
        
        model = get_whisper_model()
        
        # Asegurar float32
        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)
        
        # Whisper espera audio normalizado entre -1 y 1
        if audio_array.max() > 1.0 or audio_array.min() < -1.0:
            audio_array = audio_array / np.abs(audio_array).max()
        
        result = model.transcribe(
            audio_array,
            language=language or WHISPER_LANGUAGE,
            task=WHISPER_TASK,
            verbose=False,
            fp16=torch.cuda.is_available(),
        )
        
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "id": seg.get("id", 0),
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "text": seg.get("text", "").strip(),
            })
        
        return {
            "status": "ok",
            "text": result.get("text", "").strip(),
            "segments": segments,
            "language": result.get("language", language or "unknown"),
            "duration": round(segments[-1]["end"], 2) if segments else 0.0,
        }
        
    except Exception as e:
        logger.error(f"Error transcribiendo array: {e}")
        raise


if __name__ == "__main__":
    # Test
    import sys
    from backend.utils.timers import timer
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
        
        with timer("Transcripción"):
            result = transcribe_file(audio_file)
        
        print("\n" + "=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"Idioma: {result['language']}")
        print(f"Duración: {result['duration']}s")
        print(f"Segmentos: {len(result['segments'])}")
        print(f"\nTexto:\n{result['text']}")
        print("=" * 60)
    else:
        print("Uso: python whisper_engine.py <archivo_audio>")
