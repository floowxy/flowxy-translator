"""
Video Export Module
Genera videos con subtítulos quemados y audio TTS opcional
"""

import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def generate_srt_file(segments: List[Dict], output_path: Path, use_translation: bool = True) -> Path:
    """
    Genera archivo SRT desde segmentos de transcripción/traducción
    
    Args:
        segments: Lista de segmentos con start, end, text, translated_text
        output_path: Ruta donde guardar el SRT
        use_translation: Si True, usa translated_text; si False, usa text original
    
    Returns:
        Path al archivo SRT generado
    """
    srt_content = []
    
    for i, seg in enumerate(segments, 1):
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        
        # Elegir texto (traducido o original)
        if use_translation and "translated_text" in seg:
            text = seg["translated_text"]
        else:
            text = seg.get("text", "")
        
        # Formato de tiempo SRT: HH:MM:SS,mmm
        start_time = format_srt_time(start)
        end_time = format_srt_time(end)
        
        # Formato SRT
        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text.strip())
        srt_content.append("")  # Línea vacía entre subtítulos
    
    # Escribir archivo
    output_path.write_text("\n".join(srt_content), encoding="utf-8")
    logger.info(f"✓ Archivo SRT generado: {output_path}")
    
    return output_path


def format_srt_time(seconds: float) -> str:
    """Convierte segundos a formato SRT (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def burn_subtitles_to_video(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    subtitle_style: Optional[Dict] = None
) -> Path:
    """
    Quema subtítulos en el video usando FFmpeg
    
    Args:
        video_path: Ruta al video original
        srt_path: Ruta al archivo SRT
        output_path: Ruta del video de salida
        subtitle_style: Dict con opciones de estilo (font, size, color, etc.)
    
    Returns:
        Path al video con subtítulos quemados
    """
    # Estilo por defecto
    if subtitle_style is None:
        subtitle_style = {
            "font": "Arial",
            "font_size": 18,  # Reducido de 24 a 18 para que no ocupe tanto
            "primary_color": "&H00FFFFFF",  # Blanco
            "outline_color": "&H00000000",  # Negro
            "back_color": "&H80000000",     # Negro semi-transparente
            "bold": 1,
            "outline": 2,
            "shadow": 1,
            "alignment": 2,  # Abajo centro
        }
    
    # Construir filtro de subtítulos
    # Usar formato ASS para mejor control de estilo
    subtitle_filter = (
        f"subtitles={srt_path}:force_style='"
        f"FontName={subtitle_style['font']},"
        f"FontSize={subtitle_style['font_size']},"
        f"PrimaryColour={subtitle_style['primary_color']},"
        f"OutlineColour={subtitle_style['outline_color']},"
        f"BackColour={subtitle_style['back_color']},"
        f"Bold={subtitle_style['bold']},"
        f"Outline={subtitle_style['outline']},"
        f"Shadow={subtitle_style['shadow']},"
        f"Alignment={subtitle_style['alignment']}'"
    )
    
    # Comando FFmpeg
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", subtitle_filter,
        "-c:a", "copy",  # Copiar audio sin re-encodear
        "-c:v", "libx264",  # Codec de video
        "-preset", "medium",  # Balance velocidad/calidad
        "-crf", "23",  # Calidad (18-28, menor = mejor)
        "-y",  # Sobrescribir si existe
        str(output_path)
    ]
    
    logger.info(f"Quemando subtítulos en video...")
    logger.info(f"Comando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"✓ Subtítulos quemados exitosamente: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en FFmpeg: {e.stderr}")
        raise


async def generate_tts_audio(
    segments: List[Dict],
    output_path: Path,
    voice: str = "es-ES-AlvaroNeural",  # Voz masculina española
    rate: str = "+0%"
) -> Path:
    """
    Genera audio TTS desde segmentos traducidos usando edge-tts
    
    Args:
        segments: Lista de segmentos con translated_text y timestamps
        output_path: Ruta del archivo de audio de salida
        voice: Voz de edge-tts (es-ES-AlvaroNeural, es-ES-ElviraNeural, etc.)
        rate: Velocidad de habla (+/-N%)
    
    Returns:
        Path al archivo de audio generado
    """
    try:
        import edge_tts
    except ImportError:
        logger.error("edge-tts no está instalado. Ejecuta: pip install edge-tts")
        raise
    
    # Crear archivo temporal para cada segmento
    temp_dir = output_path.parent / "temp_tts"
    temp_dir.mkdir(exist_ok=True)
    
    segment_files = []
    
    logger.info(f"Generando audio TTS para {len(segments)} segmentos...")
    
    for i, seg in enumerate(segments):
        text = seg.get("translated_text", seg.get("text", ""))
        if not text.strip():
            continue
        
        # Archivo temporal para este segmento
        temp_file = temp_dir / f"segment_{i:04d}.mp3"
        
        # Generar TTS
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(str(temp_file))
        
        segment_files.append({
            "file": temp_file,
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "duration": seg.get("end", 0) - seg.get("start", 0)
        })
        
        if (i + 1) % 10 == 0:
            logger.info(f"  Procesado {i + 1}/{len(segments)} segmentos")
    
    logger.info(f"✓ {len(segment_files)} segmentos de audio generados")
    
    # Ahora necesitamos concatenar y sincronizar los audios
    # Esto requiere FFmpeg para crear silencios y concatenar
    await merge_tts_segments(segment_files, output_path)
    
    # Limpiar archivos temporales
    import shutil
    shutil.rmtree(temp_dir)
    
    return output_path


async def merge_tts_segments(segment_files: List[Dict], output_path: Path):
    """
    Combina segmentos TTS con silencios para sincronizar con timestamps
    """
    # Crear archivo de lista para FFmpeg concat
    concat_file = output_path.parent / "concat_list.txt"
    
    with open(concat_file, "w") as f:
        last_end = 0
        
        for seg in segment_files:
            # Agregar silencio si hay gap
            gap = seg["start"] - last_end
            if gap > 0.1:  # Si hay más de 100ms de gap
                # Generar silencio
                silence_file = output_path.parent / f"silence_{last_end:.2f}.mp3"
                await generate_silence(silence_file, gap)
                f.write(f"file '{silence_file}'\n")
            
            # Agregar segmento de audio
            f.write(f"file '{seg['file']}'\n")
            last_end = seg["end"]
    
    # Concatenar todos los archivos
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-y",
        str(output_path)
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    concat_file.unlink()  # Limpiar


async def generate_silence(output_path: Path, duration: float):
    """Genera un archivo de audio silencioso"""
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo:d={duration}",
        "-y",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def replace_video_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path
) -> Path:
    """
    Reemplaza el audio del video con el audio TTS
    
    Args:
        video_path: Video con subtítulos quemados
        audio_path: Audio TTS generado
        output_path: Video final
    
    Returns:
        Path al video final
    """
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",  # Copiar video (ya tiene subtítulos)
        "-c:a", "aac",   # Encodear audio a AAC
        "-map", "0:v:0",  # Video del primer input
        "-map", "1:a:0",  # Audio del segundo input
        "-shortest",  # Terminar cuando el más corto termine
        "-y",
        str(output_path)
    ]
    
    logger.info("Reemplazando audio del video con TTS...")
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"✓ Audio reemplazado: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error reemplazando audio: {e.stderr}")
        raise
