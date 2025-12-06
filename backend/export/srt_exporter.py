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
    Divide texto en líneas que caben en subtítulo
    
    Args:
        text: Texto a dividir
        max_chars: Caracteres máximos por línea
        max_lines: Líneas máximas
        
    Returns:
        Lista de líneas
    """
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line += word + " "
        else:
            if current_line:
                lines.append(current_line.strip())
            current_line = word + " "
            
            if len(lines) >= max_lines:
                break
    
    if current_line.strip() and len(lines) < max_lines:
        lines.append(current_line.strip())
    
    return lines


def create_srt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    use_translation: bool = False,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
) -> Path:
    """
    Crea archivo SRT de subtítulos
    
    Args:
        segments: Lista de segmentos con start, end, text
        output_path: Path del archivo de salida
        use_translation: Si usar traducción en lugar de texto original
        max_chars_per_line: Máximo de caracteres por línea
        max_lines: Máximo de líneas por subtítulo
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, 1):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            
            # Texto a usar
            if use_translation and "translated_text" in segment:
                text = segment["translated_text"]
            else:
                text = segment.get("text", "")
            
            if not text.strip():
                continue
            
            # Formatear timestamps
            start_time = format_srt_timestamp(start)
            end_time = format_srt_timestamp(end)
            
            # Wrap texto
            lines = wrap_text(text, max_chars_per_line, max_lines)
            text_content = "\n".join(lines)
            
            # Escribir subtítulo
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text_content}\n")
            f.write("\n")
    
    logger.info(f"Archivo SRT creado: {output_path}")
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
