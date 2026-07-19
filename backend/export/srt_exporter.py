"""
SRT Exporter - Exporta subtítulos en formato SubRip (.srt)
"""
import bisect
import logging
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def format_srt_timestamp(seconds: float) -> str:
    """
    Formatea timestamp a formato SRT (HH:MM:SS,mmm)
    
    Args:
        seconds: Timestamp en segundos
        
    Returns:
        String formateado (ej: "00:01:23,456")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def wrap_text(text: str, max_chars: int = 42, max_lines: int = 2) -> List[str]:
    """
    Divide texto en líneas para subtítulo.

    Nunca descarta contenido: si el texto excede max_lines, el overflow
    se añade al final de la última línea (largo pero visible) en lugar de
    desaparecer silenciosamente.
    """
    words = text.split()
    lines: List[str] = []
    current_line = ""

    for word in words:
        if not current_line or len(current_line) + len(word) + 1 <= max_chars:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "

    if current_line.strip():
        lines.append(current_line.strip())

    if not lines:
        return []

    # Si hay más líneas de las permitidas, colapsar el overflow en la última
    if len(lines) > max_lines:
        overflow = " ".join(lines[max_lines:])
        lines = lines[:max_lines]
        lines[-1] = f"{lines[-1]} {overflow}"

    return lines


def consolidate_segments(
    segments: List[Dict[str, Any]],
    use_translation: bool = True,
    max_duration_s: float = 6.0,
) -> List[Dict[str, Any]]:
    """
    Fusiona segmentos con el mismo texto y luego divide los que duran demasiado.

    Paso 1 — fusionar: N segmentos idénticos consecutivos → 1 entrada que abarca
    todo el rango temporal (sin parpadeo en límites de segmento).

    Paso 2 — dividir: si una entrada fusionada supera max_duration_s, se divide
    en chunks proporcionales distribuyendo las palabras de la traducción por
    tiempo. Evita que el subtítulo se quede "colgado" cuando el speaker habla
    mucho sin pausas ni puntuación.
    """
    if not segments:
        return []

    def _text(seg: Dict) -> str:
        if use_translation and seg.get("translated_text"):
            return seg["translated_text"].strip()
        return seg.get("text", "").strip()

    # ── Paso 1: fusionar consecutivos con el mismo texto ──────────────────────
    merged: List[Dict] = []
    current = dict(segments[0])
    for seg in segments[1:]:
        if _text(seg) == _text(current):
            current["end"] = seg["end"]
        else:
            merged.append(current)
            current = dict(seg)
    merged.append(current)

    # ── Paso 2: dividir entradas demasiado largas ──────────────────────────────
    result: List[Dict] = []
    for entry in merged:
        duration = entry["end"] - entry["start"]
        text = _text(entry)

        if duration <= max_duration_s or not text:
            result.append(entry)
            continue

        n = math.ceil(duration / max_duration_s)
        chunk_dur = duration / n
        words = text.split()

        for i in range(n):
            w_start = round(i * len(words) / n)
            w_end = round((i + 1) * len(words) / n)
            chunk_text = " ".join(words[w_start:w_end]) or text

            chunk = dict(entry)
            chunk["start"] = round(entry["start"] + i * chunk_dur, 3)
            chunk["end"] = round(entry["start"] + (i + 1) * chunk_dur, 3)
            if use_translation:
                chunk["translated_text"] = chunk_text
            else:
                chunk["text"] = chunk_text
            result.append(chunk)

    return result


_CUE_SENTENCE_SPLIT = re.compile(r'(?<=[.!?…])\s+')


def _balanced_split(text: str) -> Tuple[str, str]:
    """
    Parte el texto en dos por el punto de corte más cercano al centro.

    Prefiere cortar después de puntuación de cláusula (, ; :) — un corte en
    coma se lee natural; uno a mitad de sintagma deja la frase inconclusa.
    Nunca corta a mitad de palabra. Si no hay dónde cortar, devuelve ("", text intacto).
    """
    n = len(text)
    mid = n / 2
    best_pos, best_score = None, None

    for m in re.finditer(r'\s+', text):
        pos = m.end()
        if pos <= 1 or pos >= n:
            continue
        after_clause = text[m.start() - 1] in ',;:'
        # Distancia al centro, con bonus fuerte si el corte cae tras una coma
        score = abs(m.start() - mid) - (n * 0.2 if after_clause else 0)
        if best_score is None or score < best_score:
            best_score, best_pos = score, pos

    if best_pos is None:
        return text, ""
    return text[:best_pos].rstrip(), text[best_pos:].strip()


def _split_text_into_cues(text: str, max_chars: int) -> List[str]:
    """
    Divide el texto de un grupo en textos de cue:
    1. Corta por límites de oración (.!?…).
    2. Oraciones más largas que max_chars se parten balanceadas, con
       preferencia por comas — nunca a mitad de palabra.
    3. Oraciones cortas adyacentes se empaquetan juntas si caben.
    """
    atoms: List[str] = []

    def _explode(s: str) -> None:
        if len(s) <= max_chars:
            atoms.append(s)
            return
        a, b = _balanced_split(s)
        if not b:
            atoms.append(a)
            return
        _explode(a)
        _explode(b)

    for sentence in _CUE_SENTENCE_SPLIT.split(text.strip()):
        if sentence:
            _explode(sentence)

    cues: List[str] = []
    current = ""
    for atom in atoms:
        if current and len(current) + 1 + len(atom) <= max_chars:
            current += " " + atom
        else:
            if current:
                cues.append(current)
            current = atom
    if current:
        cues.append(current)
    return cues


def build_translated_cues(
    segments: List[Dict[str, Any]],
    max_chars: int = 84,
    min_dur_s: float = 1.0,
    max_dur_s: float = 7.0,
    max_cps: float = 20.0,
) -> List[Dict[str, Any]]:
    """
    Convierte los segmentos del DP grouper en cues sincronizados con el habla.

    El DP grouper asigna la traducción completa del grupo a todos sus
    segmentos, así que sin procesar aparecen muros de texto desalineados
    con el audio. Aquí:

    1. Se fusionan los segmentos consecutivos con la misma traducción,
       acumulando los word timestamps de Whisper de la fuente.
    2. La traducción se divide en cues de frase completa (≤ max_chars).
    3. Cada cue recibe el intervalo temporal de las palabras FUENTE que le
       corresponden por posición proporcional de caracteres → el subtítulo
       aparece mientras el hablante dice esa parte, no antes ni después.
    4. Pase de legibilidad: duración mínima, extensión hacia huecos si el
       CPS es alto, cierre de micro-huecos, sin solapes.

    Si un grupo no trae word timestamps se interpola linealmente en su rango.
    """
    # ── 1. Fusionar segmentos consecutivos con la misma traducción ────────────
    groups: List[Dict] = []
    for seg in segments:
        text = (seg.get("translated_text") or "").strip()
        if not text:
            continue
        words = [
            w for w in (seg.get("words") or [])
            if w.get("start") is not None and w.get("end") is not None
        ]
        if groups and groups[-1]["text"] == text:
            groups[-1]["end"] = float(seg.get("end", groups[-1]["end"]))
            groups[-1]["words"].extend(words)
        else:
            groups.append({
                "text": text,
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "words": list(words),
            })

    # ── 2 y 3. Dividir en cues y anclarlos al timeline de palabras fuente ─────
    # El tiempo se interpola DENTRO del tiempo hablado real (suma de duraciones
    # de palabra, ignorando pausas): un cue con el 30% de los caracteres recibe
    # el 30% del habla del grupo. Esto evita la cuantización por palabra entera
    # (cues de 0.3s con mucho texto) y reparte el CPS uniformemente en el grupo.
    result: List[Dict] = []
    for g in groups:
        texts = _split_text_into_cues(g["text"], max_chars)
        if not texts:
            continue
        total_chars = sum(len(t) for t in texts)
        words = g["words"]
        # Cada palabra se extiende hasta el inicio de la siguiente: las
        # micro-pausas intra-grupo (< 0.5s, si no el DP habría cortado) cuentan
        # como tiempo de lectura y los cues quedan contiguos, sin parpadeo.
        durs = []
        for i, w in enumerate(words):
            w_dur = max(float(w["end"]) - float(w["start"]), 0.0)
            if i + 1 < len(words):
                w_dur = max(w_dur, float(words[i + 1]["start"]) - float(w["start"]))
            durs.append(w_dur)
        spoken_total = sum(durs)

        if spoken_total <= 0:
            # Sin word timestamps útiles: interpolación lineal en el rango del grupo
            dur = max(g["end"] - g["start"], 0.0)
            consumed = 0
            for t in texts:
                c_start = g["start"] + dur * consumed / total_chars
                consumed += len(t)
                c_end = g["start"] + dur * consumed / total_chars
                result.append({"start": c_start, "end": c_end, "text": t})
            continue

        # Offset acumulado de habla al inicio de cada palabra
        cum: List[float] = []
        acc = 0.0
        for d in durs:
            cum.append(acc)
            acc += d

        def _time_at(offset: float, is_end: bool) -> float:
            """Tiempo real para un offset de habla acumulada [0, spoken_total].

            En un borde exacto entre palabras, el inicio de cue se ancla a la
            palabra siguiente y el fin a la anterior — así las pausas reales
            entre palabras quedan sin subtítulo en los límites de cue.
            """
            eps = 1e-9
            i = bisect.bisect_right(cum, offset - eps if is_end else offset + eps) - 1
            i = min(max(i, 0), len(words) - 1)
            within = min(offset - cum[i], durs[i])
            return float(words[i]["start"]) + max(within, 0.0)

        def _emit(text: str, off_a: float, off_b: float) -> None:
            t0 = _time_at(off_a, is_end=False)
            t1 = _time_at(off_b, is_end=True)
            if t1 - t0 > max_dur_s:
                a, b = _balanced_split(text)
                if b:
                    off_mid = off_a + (off_b - off_a) * len(a) / len(text)
                    _emit(a, off_a, off_mid)
                    _emit(b, off_mid, off_b)
                    return
            result.append({"start": t0, "end": t1, "text": text})

        consumed = 0
        for t in texts:
            off_a = spoken_total * consumed / total_chars
            consumed += len(t)
            off_b = spoken_total * consumed / total_chars
            _emit(t, off_a, off_b)

    # ── 4. Pase de legibilidad ────────────────────────────────────────────────
    for k, c in enumerate(result):
        next_start = result[k + 1]["start"] if k + 1 < len(result) else None
        room = next_start if next_start is not None else c["end"] + min_dur_s

        # Duración mínima, sin pisar el siguiente cue
        if c["end"] - c["start"] < min_dur_s:
            c["end"] = min(c["start"] + min_dur_s, room)

        # CPS alto → dar más tiempo de lectura si hay hueco disponible
        dur = max(c["end"] - c["start"], 1e-3)
        if len(c["text"]) / dur > max_cps:
            c["end"] = min(c["start"] + len(c["text"]) / max_cps, room)

        # Cerrar micro-huecos (evita parpadeo entre cues consecutivos)
        if next_start is not None and 0 < next_start - c["end"] < 0.3:
            c["end"] = next_start

        # Nunca solapar
        if next_start is not None and c["end"] > next_start:
            c["end"] = next_start

        c["start"] = round(c["start"], 3)
        c["end"] = round(c["end"], 3)

    for c in result:
        c["translated_text"] = c["text"]

    return result


def create_srt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    use_translation: bool = False,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
    consolidate: bool = False,
    max_duration_s: float = 6.0,
) -> Path:
    """
    Crea archivo SRT de subtítulos.

    consolidate=True con use_translation=True: reconstruye cues alineados al
    habla desde los grupos del DP grouper (build_translated_cues). Con texto
    original solo fusiona/divide segmentos idénticos (consolidate_segments).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if consolidate and use_translation:
        segs = build_translated_cues(
            segments,
            max_chars=max_chars_per_line * max_lines,
            max_dur_s=max_duration_s,
        )
    elif consolidate:
        segs = consolidate_segments(segments, use_translation, max_duration_s)
    else:
        segs = segments

    with open(output_path, "w", encoding="utf-8") as f:
        counter = 1
        for segment in segs:
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)

            if use_translation and "translated_text" in segment:
                text = segment["translated_text"]
            else:
                text = segment.get("text", "")

            if not text.strip():
                continue

            lines = wrap_text(text, max_chars_per_line, max_lines)
            text_content = "\n".join(lines)

            f.write(f"{counter}\n")
            f.write(f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}\n")
            f.write(f"{text_content}\n")
            f.write("\n")
            counter += 1

    logger.info(f"Archivo SRT creado: {output_path} ({counter - 1} entradas)")
    return output_path


def create_bilingual_srt(
    segments: List[Dict[str, Any]],
    output_path: Path,
) -> Path:
    """
    Crea archivo SRT bilingüe (original + traducción)
    
    Args:
        segments: Lista de segmentos con text y translated_text
        output_path: Path del archivo de salida
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, 1):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            
            original = segment.get("text", "").strip()
            translated = segment.get("translated_text", "").strip()
            
            if not original:
                continue
            
            # Timestamps
            start_time = format_srt_timestamp(start)
            end_time = format_srt_timestamp(end)
            
            # Ambos textos
            text_content = original
            if translated:
                text_content += f"\n{translated}"
            
            # Escribir
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text_content}\n")
            f.write("\n")
    
    logger.info(f"Archivo SRT bilingüe creado: {output_path}")
    return output_path


if __name__ == "__main__":
    # Test
    test_segments = [
        {
            "start": 0.0,
            "end": 2.5,
            "text": "Hello, this is a test.",
            "translated_text": "Hola, esto es una prueba.",
        },
        {
            "start": 2.5,
            "end": 5.0,
            "text": "We are creating subtitles.",
            "translated_text": "Estamos creando subtítulos.",
        },
        {
            "start": 5.0,
            "end": 7.8,
            "text": "This is the third subtitle with a longer text that needs to be wrapped properly.",
            "translated_text": "Este es el tercer subtítulo con un texto más largo que necesita ser dividido correctamente.",
        },
    ]
    
    output_dir = Path("/tmp/flowxy_test")
    output_dir.mkdir(exist_ok=True)
    
    # Test SRT original
    create_srt(test_segments, output_dir / "test_original.srt", use_translation=False)
    
    # Test SRT traducido
    create_srt(test_segments, output_dir / "test_translated.srt", use_translation=True)
    
    # Test SRT bilingüe
    create_bilingual_srt(test_segments, output_dir / "test_bilingual.srt")
    
    print("✓ Archivos SRT creados en:", output_dir)
