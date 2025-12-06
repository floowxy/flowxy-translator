"""
Translation utilities - Funciones helper para traducción
"""
import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


def chunk_text_for_translation(
    text: str,
    max_length: int = 400,
) -> List[str]:
    """
    Divide texto en chunks para traducción
    Respeta límites de oraciones
    
    Args:
        text: Texto a dividir
        max_length: Longitud máxima por chunk
        
    Returns:
        Lista de chunks
    """
    # Dividir por oraciones
    sentences = re.split(r'([.!?]+\s+)', text)
    
    chunks = []
    current_chunk = ""
    
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i].strip()
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""
        full_sentence = sentence + punct
        
        if len(current_chunk) + len(full_sentence) > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = full_sentence
        else:
            current_chunk += full_sentence
    
    # Última oración
    if sentences and sentences[-1].strip():
        current_chunk += sentences[-1].strip()
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def merge_translated_chunks(chunks: List[str]) -> str:
    """
    Merge chunks traducidos en texto único
    
    Args:
        chunks: Lista de chunks traducidos
        
    Returns:
        Texto completo merged
    """
    return " ".join(chunk.strip() for chunk in chunks if chunk.strip())


def preserve_formatting(
    original: str,
    translated: str,
) -> str:
    """
    Intenta preservar formato del original en la traducción
    
    Args:
        original: Texto original
        translated: Texto traducido
        
    Returns:
        Texto traducido con formato ajustado
    """
    # Preservar líneas nuevas
    if "\n" in original:
        # Contar líneas nuevas en original
        original_lines = original.count("\n")
        translated_lines = translated.count("\n")
        
        if translated_lines < original_lines:
            # Agregar líneas nuevas aproximadas
            # (implementación simple)
            pass
    
    # Por ahora solo retorna traducido
    # Mejoras futuras: preservar capitalización, espacios, etc.
    return translated


def detect_language_pair(
    source_lang: str,
    target_lang: str,
) -> tuple[str, str]:
    """
    Valida y normaliza par de idiomas
    
    Args:
        source_lang: Idioma fuente
        target_lang: Idioma destino
        
    Returns:
        Tuple (source_normalized, target_normalized)
    """
    # Mapeo de códigos comunes
    lang_map = {
        "spanish": "es",
        "english": "en",
        "french": "fr",
        "german": "de",
        "italian": "it",
        "portuguese": "pt",
        "russian": "ru",
        "japanese": "ja",
        "chinese": "zh",
        "korean": "ko",
        "arabic": "ar",
    }
    
    source_normalized = lang_map.get(source_lang.lower(), source_lang.lower())
    target_normalized = lang_map.get(target_lang.lower(), target_lang.lower())
    
    return source_normalized, target_normalized


def estimate_translation_time(
    text_length: int,
    chars_per_second: float = 100.0,
) -> float:
    """
    Estima tiempo de traducción
    
    Args:
        text_length: Longitud del texto en caracteres
        chars_per_second: Velocidad de traducción estimada
        
    Returns:
        Tiempo estimado en segundos
    """
    return text_length / chars_per_second


if __name__ == "__main__":
    # Test
    test_text = """
    This is a test sentence. This is another sentence! 
    And a third one? Here we have more text to translate.
    This should be split into appropriate chunks.
    """
    
    chunks = chunk_text_for_translation(test_text, max_length=50)
    print(f"Original length: {len(test_text)}")
    print(f"Chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i} (len={len(chunk)}):")
        print(f"  {chunk}")
