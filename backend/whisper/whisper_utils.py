"""
Whisper utilities - Funciones helper para procesamiento de transcripciones
"""
import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


def merge_segments(
    segments: List[Dict[str, Any]],
    max_length: int = 200,
    max_duration: float = 10.0,
) -> List[Dict[str, Any]]:
    """
    Merge segmentos cortos en segmentos más largos
    
    Args:
        segments: Lista de segmentos de Whisper
        max_length: Longitud máxima de caracteres por segmento merged
        max_duration: Duración máxima en segundos por segmento merged
        
    Returns:
        Lista de segmentos merged
    """
    if not segments:
        return []
    
    merged = []
    current = {
        "start": segments[0]["start"],
        "end": segments[0]["end"],
        "text": segments[0]["text"],
    }
    
    for segment in segments[1:]:
        # Calcular si agregar a current
        merged_text = current["text"] + " " + segment["text"]
        merged_duration = segment["end"] - current["start"]
        
        if (
            len(merged_text) <= max_length
            and merged_duration <= max_duration
        ):
            # Merge
            current["end"] = segment["end"]
            current["text"] = merged_text
        else:
            # Guardar current y empezar nuevo
            merged.append(current)
            current = {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
    
    # Agregar último
    merged.append(current)
    
    logger.debug(f"Merged {len(segments)} → {len(merged)} segmentos")
    return merged


def clean_text(text: str) -> str:
    """
    Limpia texto de transcripción
    
    Args:
        text: Texto a limpiar
        
    Returns:
        Texto limpio
    """
    # Remover espacios dobles
    text = re.sub(r'\s+', ' ', text)
    
    # Remover espacios antes de puntuación
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    # Capitalizar primera letra de oraciones
    text = re.sub(r'(^|[.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
    
    return text.strip()


def split_by_sentences(text: str) -> List[str]:
    """
    Divide texto en oraciones
    
    Args:
        text: Texto a dividir
        
    Returns:
        Lista de oraciones
    """
    # Regex para detectar fin de oración
    sentences = re.split(r'([.!?]+\s+)', text)
    
    result = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i].strip()
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""
        if sentence:
            result.append(sentence + punct.strip())
    
    # Última oración
    if sentences and sentences[-1].strip():
        result.append(sentences[-1].strip())
    
    return result


def format_timestamp(seconds: float, format: str = "srt") -> str:
    """
    Formatea timestamp a string
    
    Args:
        seconds: Segundos
        format: "srt" o "vtt"
        
    Returns:
        String formateado (ej: "00:01:23,456" para SRT)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    if format == "srt":
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    elif format == "vtt":
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def detect_language_from_text(text: str) -> str:
    """
    Intenta detectar idioma de texto usando langdetect
    
    Args:
        text: Texto a analizar
        
    Returns:
        Código de idioma (ej: "en", "es")
    """
    try:
        from langdetect import detect
        lang = detect(text)
        return lang
    except Exception as e:
        logger.warning(f"Error detectando idioma: {e}")
        return "unknown"


def calculate_word_timestamps(segment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calcula timestamps de palabras si no están disponibles
    
    Args:
        segment: Segmento de Whisper
        
    Returns:
        Lista de palabras con timestamps
    """
    if "words" in segment and segment["words"]:
        return segment["words"]
    
    # Aproximación simple si no hay word timestamps
    text = segment["text"].strip()
    words = text.split()
    
    start = segment["start"]
    end = segment["end"]
    duration = end - start
    
    word_duration = duration / len(words) if words else 0
    
    result = []
    current_time = start
    
    for word in words:
        result.append({
            "word": word,
            "start": round(current_time, 2),
            "end": round(current_time + word_duration, 2),
            "probability": 1.0,  # Desconocido
        })
        current_time += word_duration
    
    return result


if __name__ == "__main__":
    # Test
    test_segments = [
        {"start": 0.0, "end": 1.5, "text": "Hola"},
        {"start": 1.5, "end": 2.8, "text": "¿cómo estás?"},
        {"start": 2.8, "end": 4.2, "text": "Bien gracias"},
    ]
    
    print("Segmentos originales:", len(test_segments))
    merged = merge_segments(test_segments, max_length=100, max_duration=5.0)
    print("Segmentos merged:", len(merged))
    print(merged)
    
    print("\nTimestamps:")
    print(f"SRT: {format_timestamp(123.456, 'srt')}")
    print(f"VTT: {format_timestamp(123.456, 'vtt')}")
