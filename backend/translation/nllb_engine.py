"""
NLLB Translation Engine - Motor de traducción GPU-optimizado
Usa NLLB-200 con CTranslate2 para RTX 4060 Ti
"""
import logging
from functools import lru_cache
from math import ceil
from typing import Callable, List, Optional, Dict
from pathlib import Path

import torch

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
def _load_nllb_model():
    """
    Carga el modelo NLLB con Transformers en CPU (cached, una sola vez).

    Se carga en CPU y luego se mueve a GPU on-demand desde
    get_nllb_model(), para poder liberar la VRAM cuando no se usa
    (ver offload_nllb_model).
    """
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        logger.info(f"Cargando NLLB {NLLB_MODEL_NAME} (cpu)")

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

        if get_device() == "cuda":
            model = model.half()  # float16 para ahorrar memoria

        logger.info(f"✓ Modelo NLLB cargado: {NLLB_MODEL_NAME}")
        return model, tokenizer

    except Exception as e:
        logger.error(f"Error cargando modelo NLLB: {e}")
        raise


def get_nllb_model():
    """
    Obtiene el modelo NLLB listo para usar en el device configurado.

    Whisper y NLLB no se usan simultáneamente, así que antes de mover
    NLLB a GPU se libera la VRAM ocupada por Whisper (si estaba cargado).
    """
    model, tokenizer = _load_nllb_model()
    device = get_device()

    if device == "cuda" and next(model.parameters()).device.type != "cuda":
        from backend.whisper.whisper_engine import offload_whisper_model
        offload_whisper_model()

        logger.info(f"Moviendo NLLB {NLLB_MODEL_NAME} a {device}")
        model = model.to(device)
        torch.cuda.empty_cache()
        logger.info(f"✓ Device: {device}")

    return model, tokenizer


def preload_to_cpu() -> None:
    """Carga el modelo en CPU RAM sin moverlo a GPU. Elimina el cold-start del primer request."""
    _load_nllb_model()
    logger.info(f"✓ NLLB {NLLB_MODEL_NAME} precargado en CPU")


def offload_nllb_model():
    """Mueve el modelo NLLB a CPU para liberar VRAM (si está cargado)."""
    if _load_nllb_model.cache_info().currsize == 0:
        return

    model, _ = _load_nllb_model()
    if next(model.parameters()).device.type != "cpu":
        logger.info("Liberando VRAM: moviendo NLLB a CPU")
        model.to("cpu")
        torch.cuda.empty_cache()


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
    progress_callback: Optional[Callable[[float], None]] = None,
) -> List[Dict]:
    """Traduce una lista de segmentos en batches. Llama progress_callback(0–1) por batch."""
    if not segments:
        return []

    texts, indices = [], []
    for i, segment in enumerate(segments):
        text = segment.get("text", "").strip()
        if text:
            texts.append(text)
            indices.append(i)

    translations = [""] * len(segments)
    total_batches = max(1, ceil(len(texts) / NLLB_BATCH_SIZE))

    for batch_num, start in enumerate(range(0, len(texts), NLLB_BATCH_SIZE)):
        batch_texts = texts[start:start + NLLB_BATCH_SIZE]
        batch_indices = indices[start:start + NLLB_BATCH_SIZE]

        try:
            batch_translations = translate_batch(batch_texts, source_lang, target_lang)
            for idx, translated in zip(batch_indices, batch_translations):
                translations[idx] = translated
        except Exception as e:
            logger.warning(f"Batch {batch_num + 1} falló ({e}), reintentando segmento a segmento...")
            for sub_text, sub_idx in zip(batch_texts, batch_indices):
                try:
                    sub_result = translate_batch([sub_text], source_lang, target_lang)
                    translations[sub_idx] = sub_result[0] if sub_result else ""
                except Exception as e2:
                    logger.error(f"Segmento {sub_idx} falló también: {e2}")
                    translations[sub_idx] = ""

        if progress_callback:
            progress_callback((batch_num + 1) / total_batches)

    return [
        {**segment, "translated_text": translations[i]}
        for i, segment in enumerate(segments)
    ]


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
