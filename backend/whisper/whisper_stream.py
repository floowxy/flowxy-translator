"""
Whisper Stream - Transcripción en streaming (placeholder para futuras mejoras)
"""
import logging
from pathlib import Path
from typing import Optional, Iterator, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


def transcribe_stream(
    audio_stream: Iterator[np.ndarray],
    sample_rate: int = 16000,
    chunk_length_s: float = 30.0,
) -> Iterator[Dict[str, Any]]:
    """
    Transcribe audio en streaming (implementación futura)
    
    Args:
        audio_stream: Iterator de chunks de audio
        sample_rate: Sample rate del audio
        chunk_length_s: Longitud de cada chunk en segundos
        
    Yields:
        Diccionarios con resultados parciales de transcripción
    """
    logger.warning("Streaming transcription not implemented yet")
    
    # Placeholder - por ahora solo acumula y procesa al final
    from backend.whisper.whisper_engine import transcribe_array
    
    accumulated_audio = []
    
    for chunk in audio_stream:
        accumulated_audio.append(chunk)
    
    if accumulated_audio:
        full_audio = np.concatenate(accumulated_audio)
        result = transcribe_array(full_audio, sample_rate)
        yield result


# Placeholder para futuras implementaciones de streaming real-time
