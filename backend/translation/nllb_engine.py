"""
NLLB Translation Engine - Motor de traducción GPU-optimizado
Usa NLLB-200 con CTranslate2 para RTX 4060 Ti
"""
import logging
from functools import lru_cache
from typing import List, Optional, Dict
from pathlib import Path

from backend.config import (
    NLLB_MODEL_DIR,
    NLLB_MODEL_SIZE,
    NLLB_MODEL_NAME,
    NLLB_BEAM_SIZE,
    NLLB_MAX_LENGTH,
    NLLB_BATCH_SIZE,
    NLLB_LANG_CODES,
    COMPUTE_TYPE,
    get_device,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_nllb_model():
    """
    Carga el modelo NLLB con Transformers (evita problemas con ctranslate2)
    
    Returns:
        Tuple (model, tokenizer)
    """
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        
        device = get_device()
        
        logger.info(f"Cargando NLLB {NLLB_MODEL_NAME} en {device}")
        
        # Usar transformers directamente (más compatible)
        tokenizer = AutoTokenizer.from_pretrained(
            NLLB_MODEL_NAME,
            cache_dir=str(NLLB_MODEL_DIR),
            src_lang="eng_Latn",
        )
        
        model = AutoModelForSeq2SeqLM.from_pretrained(
            NLLB_MODEL_NAME,
            cache_dir=str(NLLB_MODEL_DIR),
        )
        
        # Mover a GPU si está disponible
        if device == "cuda":
            import torch
            model = model.to("cuda")
            model = model.half()  # float16 para ahorrar memoria
        
        logger.info(f"✓ Modelo NLLB cargado en {device}")
        return model, tokenizer
            
    except Exception as e:
        logger.error(f"Error cargando modelo NLLB: {e}")
        raise


def get_lang_code(lang: str) -> str:
    """
    Convierte código ISO a código NLLB
    
    Args:
        lang: Código ISO (ej: "es", "en")
        
    Returns:
        Código NLLB (ej: "spa_Latn", "eng_Latn")
    """
    return NLLB_LANG_CODES.get(lang, lang)


def translate_text(
    text: str,
    source_lang: str = "en",
    target_lang: str = "es",
    beam_size: Optional[int] = None,
) -> Dict[str, str]:
    """
    Traduce texto usando NLLB
    
    Args:
        text: Texto a traducir
        source_lang: Idioma fuente (código ISO)
        target_lang: Idioma destino (código ISO)
        beam_size: Tamaño del beam search
        
    Returns:
        Dict con traducción:
        {
            "status": "ok",
            "source_text": "...",
            "translated_text": "...",
            "source_lang": "en",
            "target_lang": "es"
        }
    """
    if not text or not text.strip():
        return {
            "status": "ok",
            "source_text": text,
            "translated_text": "",
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
    
    if beam_size is None:
        beam_size = NLLB_BEAM_SIZE
    
    source_code = get_lang_code(source_lang)
    target_code = get_lang_code(target_lang)
    
    logger.info(f"Traduciendo: {source_code} → {target_code}")
    logger.info(f"  Longitud texto: {len(text)} caracteres")
    
    try:
        model, tokenizer = get_nllb_model()
        
        # Configurar tokenizer
        tokenizer.src_lang = source_code
        
        # Tokenizar
        inputs = tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=NLLB_MAX_LENGTH,
        )
        
        # Mover a GPU si está disponible
        device = get_device()
        if device == "cuda":
            import torch
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # Generar traducción
        translated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.lang_code_to_id[target_code],
            max_length=NLLB_MAX_LENGTH,
            num_beams=beam_size,
            early_stopping=True,
        )
        
        # Decodificar
        translated_text = tokenizer.batch_decode(
            translated_tokens,
            skip_special_tokens=True,
        )[0]
        
        logger.info(f"✓ Traducción completada")
        logger.info(f"  Longitud resultado: {len(translated_text)} caracteres")
        
        return {
            "status": "ok",
            "source_text": text,
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        
    except Exception as e:
        logger.error(f"Error en traducción: {e}")
        raise


def translate_segments(
    segments: List[Dict],
    source_lang: str = "en",
    target_lang: str = "es",
) -> List[Dict]:
    """
    Traduce una lista de segmentos
    
    Args:
        segments: Lista de segmentos con "text"
        source_lang: Idioma fuente
        target_lang: Idioma destino
        
    Returns:
        Lista de segmentos con traducción agregada
    """
    result_segments = []
    
    for segment in segments:
        text = segment.get("text", "").strip()
        
        if not text:
            result_segments.append({
                **segment,
                "translated_text": "",
            })
            continue
        
        try:
            translation = translate_text(text, source_lang, target_lang)
            result_segments.append({
                **segment,
                "translated_text": translation["translated_text"],
            })
        except Exception as e:
            logger.error(f"Error traduciendo segmento: {e}")
            result_segments.append({
                **segment,
                "translated_text": f"[ERROR: {str(e)}]",
            })
    
    return result_segments


def translate_batch(
    texts: List[str],
    source_lang: str = "en",
    target_lang: str = "es",
) -> List[str]:
    """
    Traduce múltiples textos en batch (más eficiente)
    
    Args:
        texts: Lista de textos a traducir
        source_lang: Idioma fuente
        target_lang: Idioma destino
        
    Returns:
        Lista de traducciones
    """
    if not texts:
        return []
    
    source_code = get_lang_code(source_lang)
    target_code = get_lang_code(target_lang)
    
    logger.info(f"Traduciendo batch de {len(texts)} textos")
    
    try:
        model, tokenizer = get_nllb_model()
        
        tokenizer.src_lang = source_code
        
        # Tokenizar batch
        inputs = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=NLLB_MAX_LENGTH,
        )
        
        # GPU
        device = get_device()
        if device == "cuda":
            import torch
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        # Generar
        translated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.lang_code_to_id[target_code],
            max_length=NLLB_MAX_LENGTH,
            num_beams=NLLB_BEAM_SIZE,
        )
        
        # Decodificar
        translations = tokenizer.batch_decode(
            translated_tokens,
            skip_special_tokens=True,
        )
        
        logger.info(f"✓ Batch traducido")
        return translations
        
    except Exception as e:
        logger.error(f"Error en traducción batch: {e}")
        raise


if __name__ == "__main__":
    # Test
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        
        from backend.utils.timers import timer
        
        with timer("Traducción"):
            result = translate_text(text, source_lang="en", target_lang="es")
        
        print("\n" + "=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"Original ({result['source_lang']}): {result['source_text']}")
        print(f"Traducido ({result['target_lang']}): {result['translated_text']}")
        print("=" * 60)
    else:
        print("Uso: python nllb_engine.py <texto en inglés>")
        print('Ejemplo: python nllb_engine.py "Hello, how are you?"')
