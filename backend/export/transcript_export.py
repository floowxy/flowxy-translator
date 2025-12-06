"""
Transcript Export - Exporta transcripciones en formatos TXT y JSON
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def export_txt(
    text: str,
    output_path: Path,
    include_metadata: bool = True,
) -> Path:
    """
    Exporta transcripción como TXT simple
    
    Args:
        text: Texto a exportar
        output_path: Path de salida
        include_metadata: Si incluir metadata (timestamp, etc)
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        if include_metadata:
            f.write("=" * 60 + "\n")
            f.write("FLOWXY-TRANSLATOR - Transcripción\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
        
        f.write(text)
        
        if include_metadata:
            f.write("\n\n" + "=" * 60 + "\n")
    
    logger.info(f"Archivo TXT creado: {output_path}")
    return output_path


def export_bilingual_txt(
    original_text: str,
    translated_text: str,
    output_path: Path,
    source_lang: str = "en",
    target_lang: str = "es",
) -> Path:
    """
    Exporta transcripción bilingüe
    
    Args:
        original_text: Texto original
        translated_text: Texto traducido
        output_path: Path de salida
        source_lang: Idioma fuente
        target_lang: Idioma destino
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("FLOWXY-TRANSLATOR - Transcripción Bilingüe\n")
        f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"ORIGINAL ({source_lang.upper()}):\n")
        f.write("-" * 60 + "\n")
        f.write(original_text)
        f.write("\n\n")
        
        f.write(f"TRADUCCIÓN ({target_lang.upper()}):\n")
        f.write("-" * 60 + "\n")
        f.write(translated_text)
        f.write("\n\n")
        
        f.write("=" * 60 + "\n")
    
    logger.info(f"Archivo TXT bilingüe creado: {output_path}")
    return output_path


def export_json(
    data: Dict[str, Any],
    output_path: Path,
    pretty: bool = True,
) -> Path:
    """
    Exporta datos completos en formato JSON
    
    Args:
        data: Datos a exportar
        output_path: Path de salida
        pretty: Si formated con indent
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Agregar metadata
    export_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "tool": "flowxy-translator",
        },
        **data,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        else:
            json.dump(export_data, f, ensure_ascii=False)
    
    logger.info(f"Archivo JSON creado: {output_path}")
    return output_path


def export_segments_txt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    use_translation: bool = False,
    include_timestamps: bool = True,
) -> Path:
    """
    Exporta segmentos como TXT con timestamps
    
    Args:
        segments: Lista de segmentos
        output_path: Path de salida
        use_translation: Si usar traducción
        include_timestamps: Si incluir timestamps
        
    Returns:
        Path al archivo creado
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("FLOWXY-TRANSLATOR - Transcripción por Segmentos\n")
        f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        for i, segment in enumerate(segments, 1):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            
            if use_translation and "translated_text" in segment:
                text = segment["translated_text"]
            else:
                text = segment.get("text", "")
            
            if not text.strip():
                continue
            
            if include_timestamps:
                f.write(f"[{i}] [{start:.2f}s - {end:.2f}s]\n")
            else:
                f.write(f"[{i}]\n")
            
            f.write(f"{text.strip()}\n\n")
        
        f.write("=" * 60 + "\n")
    
    logger.info(f"Archivo TXT de segmentos creado: {output_path}")
    return output_path


if __name__ == "__main__":
    # Test
    test_data = {
        "status": "ok",
        "text": "This is a test transcription.",
        "translated_text": "Esta es una transcripción de prueba.",
        "language": "en",
        "duration": 5.0,
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 2.5,
                "text": "This is a test.",
                "translated_text": "Esta es una prueba.",
            },
            {
                "id": 1,
                "start": 2.5,
                "end": 5.0,
                "text": "Testing export functions.",
                "translated_text": "Probando funciones de exportación.",
            },
        ],
    }
    
    output_dir = Path("/tmp/flowxy_test")
    output_dir.mkdir(exist_ok=True)
    
    # Test TXT
    export_txt(test_data["text"], output_dir / "test.txt")
    
    # Test bilingüe
    export_bilingual_txt(
        test_data["text"],
        test_data["translated_text"],
        output_dir / "test_bilingual.txt",
    )
    
    # Test JSON
    export_json(test_data, output_dir / "test.json")
    
    # Test segmentos
    export_segments_txt(test_data["segments"], output_dir / "test_segments.txt")
    
    print("✓ Archivos exportados en:", output_dir)
