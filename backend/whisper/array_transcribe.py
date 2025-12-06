"""
Transcribe numpy array directly (for real-time processing)
"""
from faster_whisper import WhisperModel
import numpy as np
from typing import Dict, Any, Optional

from backend.config import (
    WHISPER_MODEL_SIZE,
    WHISPER_MODEL_DIR,
    COMPUTE_TYPE,
    get_device,
    WHISPER_BEAM_SIZE,
    WHISPER_BEST_OF,
    WHISPER_TEMPERATURE,
)


def transcribe_array(
    audio_array: np.ndarray,
    language: Optional[str] = None,
    sample_rate: int = 16000,
) -> Dict[str, Any]:
    """
    Transcribe audio from numpy array
    
    Args:
        audio_array: Float32 audio data
        language: Language code or None for auto-detect
        sample_rate: Sample rate (should be 16000 for Whisper)
        
    Returns:
        Dict with transcription result
    """
    from backend.whisper.whisper_engine import get_whisper_model
    from backend.utils.logger import get_logger
    
    logger = get_logger(__name__)
    
    model = get_whisper_model()
    
    # Ensure audio is correct format
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)
    
    # Ensure sample rate
    if sample_rate != 16000:
        logger.warning(f"Sample rate is {sample_rate}, should be 16000")
    
    # Transcribe
    segments_iter, info = model.transcribe(
        audio_array,
        language=language,
        beam_size=WHISPER_BEAM_SIZE,
        best_of=WHISPER_BEST_OF,
        temperature=WHISPER_TEMPERATURE,
    )
    
    # Collect segments
    segments = []
    text_parts = []
    
    for seg in segments_iter:
        segments.append({
            "id": seg.id,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        text_parts.append(seg.text.strip())
    
    full_text = " ".join(text_parts)
    
    return {
        "status": "ok",
        "text": full_text,
        "segments": segments,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
    }
