"""
Language detection - Detección de idioma de texto
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def detect_language(text: str, use_whisper_info: bool = True) -> Optional[str]:
    """
    Detecta el idioma de un texto
    
    Args:
        text: Texto a analizar
        use_whisper_info: Si usar info de Whisper como primaria
        
    Returns:
        Código ISO del idioma (ej: "en", "es") o None
    """
    if not text or len(text.strip()) < 10:
        logger.warning("Texto muy corto para detección confiable")
        return None
    
    try:
        from langdetect import detect, DetectorFactory
        
        # Seed para resultados consistentes
        DetectorFactory.seed = 0
        
        lang = detect(text)
        logger.info(f"Idioma detectado: {lang}")
        return lang
        
    except Exception as e:
        logger.warning(f"Error en detección de idioma: {e}")
        return None


def detect_language_with_confidence(text: str) -> tuple[Optional[str], float]:
    """
    Detecta idioma con nivel de confianza
    
    Args:
        text: Texto a analizar
        
    Returns:
        Tuple (lang_code, confidence)
    """
    if not text or len(text.strip()) < 10:
        return None, 0.0
    
    try:
        from langdetect import detect_langs
        
        langs = detect_langs(text)
        
        if langs:
            best = langs[0]
            return best.lang, best.prob
        else:
            return None, 0.0
            
    except Exception as e:
        logger.warning(f"Error en detección: {e}")
        return None, 0.0


def is_language(text: str, expected_lang: str, threshold: float = 0.7) -> bool:
    """
    Verifica si el texto es de un idioma específico
    
    Args:
        text: Texto a verificar
        expected_lang: Código del idioma esperado
        threshold: Umbral de confianza (0-1)
        
    Returns:
        True si el texto es del idioma esperado
    """
    lang, confidence = detect_language_with_confidence(text)
    
    if lang == expected_lang and confidence >= threshold:
        return True
    
    return False


def get_language_name(lang_code: str) -> str:
    """
    Obtiene el nombre completo de un idioma
    
    Args:
        lang_code: Código ISO (ej: "es", "en")
        
    Returns:
        Nombre completo (ej: "Español", "Inglés")
    """
    lang_names = {
        "es": "Español",
        "en": "Inglés",
        "fr": "Francés",
        "de": "Alemán",
        "it": "Italiano",
        "pt": "Portugués",
        "ru": "Ruso",
        "ja": "Japonés",
        "zh": "Chino",
        "ko": "Coreano",
        "ar": "Árabe",
        "hi": "Hindi",
    }
    
    return lang_names.get(lang_code, lang_code.upper())


if __name__ == "__main__":
    # Test
    test_texts = {
        "en": "This is a test in English. Hello world!",
        "es": "Esto es una prueba en español. ¡Hola mundo!",
        "fr": "Ceci est un test en français. Bonjour le monde!",
        "de": "Dies ist ein Test auf Deutsch. Hallo Welt!",
    }
    
    print("=" * 60)
    print("TEST: Language Detection")
    print("=" * 60)
    
    for expected, text in test_texts.items():
        lang, confidence = detect_language_with_confidence(text)
        name = get_language_name(lang) if lang else "Unknown"
        
        print(f"\nTexto: {text[:50]}...")
        print(f"Esperado: {expected} ({get_language_name(expected)})")
        print(f"Detectado: {lang} ({name})")
        print(f"Confianza: {confidence:.2%}")
        print(f"Match: {'✓' if lang == expected else '✗'}")
