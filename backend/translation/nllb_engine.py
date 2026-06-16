"""
NLLB Translation Engine - Motor de traducción GPU-optimizado
Usa NLLB-200 con CTranslate2 para RTX 4060 Ti
"""
import logging
import re
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
    NLLB_REPETITION_PENALTY,
    NLLB_NO_REPEAT_NGRAM,
    NLLB_CONTEXT_AWARE,
    NLLB_LANG_CODES,
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


# Patrón de cierre de oración en la fuente (inglés)
_SENTENCE_END = re.compile(r'[.!?]["\'»]?\s*$')

# Conectores que señalan inicio de nuevo pensamiento aunque no haya puntuación previa
_CONNECTOR_START = re.compile(
    r'^(however|but |now |so |let me|let\'s|alright|okay|well |'
    r'next |then |finally|first |second |third |also |additionally|'
    r'furthermore|moreover|therefore|thus |although|though |despite|'
    r'moving on|anyway|speaking of|in fact|actually|basically|essentially|'
    r'and now|now let|so now|so let)\b',
    re.IGNORECASE,
)

# Post-procesamiento: artefactos comunes de NLLB en la traducción
_FIX_SPACE_PUNCT  = re.compile(r'\s+([.!?,;:»\)\]])')          # "hola ." → "hola."
_FIX_DOUBLE_LONG  = re.compile(r'\b(\w{4,})\s+\1\b', re.IGNORECASE)   # "función función" → "función"
_FIX_DOUBLE_SHORT = re.compile(                                  # artículos duplicados
    r'\b(el|la|de|un|una|los|las|en|es|se|le|lo)\s+\1\b',
    re.IGNORECASE,
)
_FIX_MULTI_SPACE  = re.compile(r' {2,}')


def _postprocess(text: str) -> str:
    """Limpia artefactos conocidos del output de NLLB."""
    text = _FIX_SPACE_PUNCT.sub(r'\1', text)
    text = _FIX_DOUBLE_LONG.sub(r'\1', text)
    text = _FIX_DOUBLE_SHORT.sub(r'\1', text)
    text = _FIX_MULTI_SPACE.sub(' ', text)
    return text.strip()


def _translate_one(text: str, source_lang: str, target_lang: str) -> str:
    """Traduce un texto con todos los parámetros de calidad configurados."""
    source_code = get_lang_code(source_lang)
    target_code = get_lang_code(target_lang)

    model, tokenizer = get_nllb_model()
    tokenizer.src_lang = source_code

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=NLLB_MAX_LENGTH,
    )

    device = get_device()
    if device == "cuda":
        inputs = {k: v.to("cuda") for k, v in inputs.items()}

    tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.lang_code_to_id[target_code],
        max_length=NLLB_MAX_LENGTH,
        num_beams=NLLB_BEAM_SIZE,
        repetition_penalty=NLLB_REPETITION_PENALTY,
        no_repeat_ngram_size=NLLB_NO_REPEAT_NGRAM,
    )

    return _postprocess(tokenizer.decode(tokens[0], skip_special_tokens=True))


def _extract_context_portion(full: str, ctx_src: str, tgt_src: str) -> str:
    """
    Extrae la parte del objetivo de una traducción conjunta 'contexto + objetivo'.

    Estrategia 1 (con puntuación): divide en oraciones, toma las últimas proporcionales.
    Estrategia 2 (sin puntuación): NLLB a veces omite el punto final — divide por
    palabras para evitar devolver el contexto completo como parte del subtítulo.
    """
    ctx_w = len(ctx_src.split())
    tgt_w = len(tgt_src.split())
    total_w = ctx_w + tgt_w
    if total_w == 0 or tgt_w == 0:
        return full.strip()

    sentences = re.split(r'(?<=[.!?])\s+', full.strip())
    if len(sentences) > 1:
        target_count = max(1, round(len(sentences) * tgt_w / total_w))
        return ' '.join(sentences[-target_count:]).strip() or full.strip()

    # Sin puntuación de cierre: división proporcional por palabras
    words = full.split()
    if not words:
        return full.strip()
    start = max(0, round(len(words) * ctx_w / total_w))
    return ' '.join(words[start:]).strip() or full.strip()


_PAUSE_THRESHOLD_S = 0.5  # segundos de silencio para cerrar grupo


def _dp_group_segments(segments: List[Dict], max_words: int = 60) -> List[List[int]]:
    """
    Agrupación dinámica de segmentos en unidades de traducción óptimas.

    Señales de cierre de grupo (greedy O(n)):
      1. El texto termina con .!?             → oración completa
      2. El grupo supera max_words            → evitar truncado del modelo
      3. El siguiente segmento empieza con
         un conector ("However,", "But ", …) → nuevo pensamiento
      4. Hay un silencio ≥ 0.5 s entre
         el segmento anterior y el actual     → pausa natural entre frases
    """
    groups: List[List[int]] = []
    current: List[int] = []
    current_words = 0

    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()

        # Señales que indican que este segmento ABRE un nuevo grupo
        if current:
            is_connector = bool(_CONNECTOR_START.match(text))
            prev_end = segments[i - 1].get("end", 0)
            curr_start = seg.get("start", 0)
            is_after_pause = (curr_start - prev_end) >= _PAUSE_THRESHOLD_S

            if is_connector or is_after_pause:
                groups.append(current)
                current, current_words = [], 0

        current.append(i)
        current_words += len(text.split()) if text else 0

        closes_sentence = bool(_SENTENCE_END.search(text))
        too_long = current_words >= max_words

        if closes_sentence or too_long:
            groups.append(current)
            current, current_words = [], 0

    if current:
        groups.append(current)

    return groups


def translate_segments(
    segments: List[Dict],
    source_lang: str = "en",
    target_lang: str = "es",
    progress_callback: Optional[Callable[[float], None]] = None,
) -> List[Dict]:
    """
    Traducción con agrupación dinámica y memoria inter-grupo.

    Flujo:
    1. _dp_group_segments: agrupa segmentos en unidades semánticamente completas
       (oración por oración, no bloques fijos)
    2. Cada grupo se traduce como texto unificado → mejor coherencia intra-oración
    3. El texto del grupo anterior se pasa como contexto al siguiente → memoria
       inter-grupo (pronombres, referencias, continuidad de discurso)
    4. Todos los segmentos del grupo reciben la traducción completa del grupo

    Si NLLB_CONTEXT_AWARE=False: batch puro sin agrupación (modo rápido).
    """
    if not segments:
        return []

    if not NLLB_CONTEXT_AWARE:
        # ── Modo batch rápido sin contexto (fallback) ────────────────────────
        texts, indices, translations = [], [], [""] * len(segments)
        for i, seg in enumerate(segments):
            t = seg.get("text", "").strip()
            if t:
                texts.append(t)
                indices.append(i)

        total_batches = max(1, ceil(len(texts) / NLLB_BATCH_SIZE))
        for b, start in enumerate(range(0, len(texts), NLLB_BATCH_SIZE)):
            batch_t = texts[start:start + NLLB_BATCH_SIZE]
            batch_i = indices[start:start + NLLB_BATCH_SIZE]
            try:
                for idx, t in zip(batch_i, translate_batch(batch_t, source_lang, target_lang)):
                    translations[idx] = t
            except Exception as e:
                logger.warning(f"Batch {b+1} falló: {e}")
                for st, si in zip(batch_t, batch_i):
                    try:
                        translations[si] = (translate_batch([st], source_lang, target_lang) or [""])[0]
                    except Exception:
                        translations[si] = ""
            if progress_callback:
                progress_callback((b + 1) / total_batches)

        return [{**seg, "translated_text": translations[i]} for i, seg in enumerate(segments)]

    # ── Modo DP con agrupación dinámica y memoria inter-grupo ────────────────
    groups = _dp_group_segments(segments)
    n_groups = len(groups)
    translations = [""] * len(segments)
    prev_src = ""  # memoria del grupo anterior

    logger.info(f"DP grouping: {len(segments)} segmentos → {n_groups} grupos")

    for g_idx, indices in enumerate(groups):
        group_texts = [segments[i].get("text", "").strip() for i in indices]
        group_src = " ".join(t for t in group_texts if t)

        if not group_src:
            if progress_callback:
                progress_callback((g_idx + 1) / n_groups)
            continue

        # Construir fuente con contexto inter-grupo (memoria)
        src_with_ctx = f"{prev_src} {group_src}".strip() if prev_src else group_src

        try:
            full = _translate_one(src_with_ctx, source_lang, target_lang)
            group_translation = (
                _extract_context_portion(full, prev_src, group_src)
                if prev_src else full
            )
        except Exception as e:
            logger.warning(f"Grupo {g_idx+1} falló ({e}), reintentando sin contexto...")
            try:
                group_translation = _translate_one(group_src, source_lang, target_lang)
            except Exception as e2:
                logger.error(f"Grupo {g_idx+1} falló también: {e2}")
                group_translation = ""

        # Todos los segmentos del grupo reciben la traducción completa del grupo
        for i in indices:
            translations[i] = group_translation

        # Contexto inter-grupo: solo usar si el grupo terminó en oración completa.
        # Un grupo cortado por max_words da contexto de baja calidad (frase incompleta).
        if _SENTENCE_END.search(group_src):
            prev_src = group_src
        else:
            # Extraer solo la última oración completa del grupo
            parts = re.split(r'(?<=[.!?])\s+', group_src)
            prev_src = parts[-2] if len(parts) >= 2 else ""
        logger.debug(f"Grupo {g_idx+1}/{n_groups} [{len(indices)} segs]: '{group_src[:50]}...'")

        if progress_callback:
            progress_callback((g_idx + 1) / n_groups)

    return [{**seg, "translated_text": translations[i]} for i, seg in enumerate(segments)]


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
            repetition_penalty=NLLB_REPETITION_PENALTY,
            no_repeat_ngram_size=NLLB_NO_REPEAT_NGRAM,
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
