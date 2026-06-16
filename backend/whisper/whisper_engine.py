"""
Whisper Engine - Motor de transcripción GPU-optimizado con OpenAI Whisper
Optimizado para RTX 4060 Ti usando PyTorch + CUDA
"""
import logging
import subprocess
import threading
import time
from pathlib import Path
from functools import lru_cache
from typing import Callable, Dict, Any, List, Optional
import torch
import whisper

from backend.config import (
    WHISPER_MODEL_DIR,
    WHISPER_MODEL_SIZE,
    WHISPER_LANGUAGE,
    WHISPER_TASK,
    WHISPER_BEAM_SIZE,
    WHISPER_BEST_OF,
    get_device,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_whisper_model():
    """
    Carga el modelo Whisper en CPU (cached, una sola vez por proceso).

    Se carga en CPU y luego se mueve a GPU on-demand desde
    get_whisper_model(), para poder liberar la VRAM cuando no se usa
    (ver offload_whisper_model).
    """
    try:
        logger.info(f"Cargando Whisper {WHISPER_MODEL_SIZE} (cpu)")

        # Crear directorio de modelos si no existe
        WHISPER_MODEL_DIR.mkdir(exist_ok=True, parents=True)

        model = whisper.load_model(
            WHISPER_MODEL_SIZE,
            device="cpu",
            download_root=str(WHISPER_MODEL_DIR),
        )

        logger.info(f"✓ Modelo Whisper cargado: {WHISPER_MODEL_SIZE}")
        return model

    except Exception as e:
        logger.error(f"Error cargando modelo Whisper: {e}")
        raise


def get_whisper_model():
    """
    Obtiene el modelo Whisper listo para usar en el device configurado.

    Whisper y NLLB no se usan simultáneamente, así que antes de mover
    Whisper a GPU se libera la VRAM ocupada por NLLB (si estaba cargado).
    """
    model = _load_whisper_model()
    device = get_device()

    if device == "cuda" and next(model.parameters()).device.type != "cuda":
        from backend.translation.nllb_engine import offload_nllb_model
        offload_nllb_model()

        logger.info(f"Moviendo Whisper {WHISPER_MODEL_SIZE} a {device}")
        model = model.to(device)
        torch.cuda.empty_cache()
        logger.info(f"✓ Device: {device}")

    return model


def _get_audio_duration(audio_path: Path) -> float:
    """Duración del archivo con ffprobe. Rápido y soporta todos los formatos."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(audio_path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def preload_to_cpu() -> None:
    """Carga el modelo en CPU RAM sin moverlo a GPU. Elimina el cold-start del primer request."""
    _load_whisper_model()
    logger.info(f"✓ Whisper {WHISPER_MODEL_SIZE} precargado en CPU")


def offload_whisper_model():
    """Mueve el modelo Whisper a CPU para liberar VRAM (si está cargado)."""
    if _load_whisper_model.cache_info().currsize == 0:
        return

    model = _load_whisper_model()
    if next(model.parameters()).device.type != "cpu":
        logger.info("Liberando VRAM: moviendo Whisper a CPU")
        model.to("cpu")
        torch.cuda.empty_cache()


def transcribe_file(
    audio_path: Path,
    language: Optional[str] = None,
    task: str = "transcribe",
    progress_callback: Optional[Callable[[float], None]] = None,
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

    if language is None:
        language = WHISPER_LANGUAGE

    logger.info(f"Transcribiendo: {audio_path.name}")
    logger.info(f"  Language: {language or 'auto-detect'}")
    logger.info(f"  Task: {task}")

    # Progreso estimado basado en duración y velocidad del modelo
    stop_event = threading.Event()
    if progress_callback:
        duration = _get_audio_duration(audio_path)
        if duration > 0:
            # medium en RTX 4060 Ti ≈ 8x realtime; en CPU ≈ 0.5x
            speed = 8.0 if torch.cuda.is_available() else 0.5
            start_t = time.time()

            def _track_progress() -> None:
                while not stop_event.is_set():
                    elapsed = time.time() - start_t
                    progress_callback(min(0.92, elapsed * speed / duration))
                    stop_event.wait(0.4)

            threading.Thread(target=_track_progress, daemon=True).start()

    try:
        model = get_whisper_model()
        
        # Transcribir con configuración optimizada para GPU
        result = model.transcribe(
            str(audio_path),
            language=language,
            task=task,
            verbose=False,
            fp16=torch.cuda.is_available(),
            beam_size=WHISPER_BEAM_SIZE,
            best_of=WHISPER_BEST_OF,
            word_timestamps=True,  # timestamps por palabra para mejor sync de subtítulos
        )

        # Procesar segmentos
        segments: List[Dict[str, Any]] = []

        for seg in result.get("segments", []):
            segment_dict = {
                "id": seg.get("id", 0),
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "text": seg.get("text", "").strip(),
                "words": [
                    {
                        "word": w.get("word", "").strip(),
                        "start": round(w.get("start", 0.0), 2),
                        "end": round(w.get("end", 0.0), 2),
                    }
                    for w in seg.get("words", [])
                ],
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
    finally:
        stop_event.set()
        if progress_callback:
            progress_callback(1.0)


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
            beam_size=WHISPER_BEAM_SIZE,
            best_of=WHISPER_BEST_OF,
            word_timestamps=True,
        )

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "id": seg.get("id", 0),
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "text": seg.get("text", "").strip(),
                "words": [
                    {
                        "word": w.get("word", "").strip(),
                        "start": round(w.get("start", 0.0), 2),
                        "end": round(w.get("end", 0.0), 2),
                    }
                    for w in seg.get("words", [])
                ],
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
