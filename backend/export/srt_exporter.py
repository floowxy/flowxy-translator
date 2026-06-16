"""
SRT Exporter - Exporta subtítulos en formato SubRip (.srt)
"""
import logging
from pathlib import Path
from typing import List, Dict, Any

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


def consolidate_segments(segments: List[Dict[str, Any]], use_translation: bool = True) -> List[Dict[str, Any]]:
    """
    Fusiona segmentos consecutivos que tienen el mismo texto de subtítulo.

    El DP grouper asigna la misma translated_text a todos los segmentos de un
    grupo. Sin consolidar, el SRT tiene N entradas idénticas que hacen parpadear
    el subtítulo en cada límite de segmento. Con consolidar, queda una sola
    entrada que abarca todo el tiempo del grupo — aparece cuando empieza la
    oración y desaparece cuando termina.
    """
    if not segments:
        return []

    def _text(seg: Dict) -> str:
        if use_translation and seg.get("translated_text"):
            return seg["translated_text"].strip()
        return seg.get("text", "").strip()

    result: List[Dict] = []
    current = dict(segments[0])

    for seg in segments[1:]:
        if _text(seg) == _text(current):
            current["end"] = seg["end"]  # extender el rango temporal
        else:
            result.append(current)
            current = dict(seg)

    result.append(current)
    return result


def create_srt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    use_translation: bool = False,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
    consolidate: bool = False,
) -> Path:
    """
    Crea archivo SRT de subtítulos.

    consolidate=True: fusiona segmentos consecutivos con el mismo texto antes
    de escribir. Recomendado para video quemado cuando se usa el DP grouper.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    segs = consolidate_segments(segments, use_translation) if consolidate else segments

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
