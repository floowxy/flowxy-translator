"""
VTT Exporter - Exporta subtítulos en formato WebVTT (.vtt)
"""
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def format_vtt_timestamp(seconds: float) -> str:
    """
    Formatea timestamp a formato VTT (HH:MM:SS.mmm)
    
    Args:
        seconds: Timestamp en segundos
        
    Returns:
        String formateado (ej: "00:01:23.456")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def create_vtt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    use_translation: bool = False,
) -> Path:
    """
    Crea archivo VTT de subtítulos
    
    Args:
        segments: Lista de segmentos con start, end, text
        output_path: Path del archivo de salida
        use_translation: Si usar traducción
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        # Header VTT
        f.write("WEBVTT\n\n")
        
        for i, segment in enumerate(segments, 1):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            
            # Texto
            if use_translation and "translated_text" in segment:
                text = segment["translated_text"]
            else:
                text = segment.get("text", "")
            
            if not text.strip():
                continue
            
            # Timestamps
            start_time = format_vtt_timestamp(start)
            end_time = format_vtt_timestamp(end)
            
            # Escribir
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text.strip()}\n")
            f.write("\n")
    
    logger.info(f"Archivo VTT creado: {output_path}")
    return output_path


def create_bilingual_vtt(
    segments: List[Dict[str, Any]],
    output_path: Path,
) -> Path:
    """
    Crea archivo VTT bilingüe
    
    Args:
        segments: Lista de segmentos
        output_path: Path de salida
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        
        for i, segment in enumerate(segments, 1):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            
            original = segment.get("text", "").strip()
            translated = segment.get("translated_text", "").strip()
            
            if not original:
                continue
            
            start_time = format_vtt_timestamp(start)
            end_time = format_vtt_timestamp(end)
            
            # Texto bilingüe
            text_content = original
            if translated:
                text_content += f"\n{translated}"
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text_content}\n")
            f.write("\n")
    
    logger.info(f"Archivo VTT bilingüe creado: {output_path}")
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
            "text": "WebVTT subtitle format.",
            "translated_text": "Formato de subtítulos WebVTT.",
        },
    ]
    
    output_dir = Path("/tmp/flowxy_test")
    output_dir.mkdir(exist_ok=True)
    
    create_vtt(test_segments, output_dir / "test.vtt")
    create_bilingual_vtt(test_segments, output_dir / "test_bilingual.vtt")
    
    print("✓ Archivos VTT creados")
