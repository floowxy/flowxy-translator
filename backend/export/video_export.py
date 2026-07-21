"""
Video Export Module
Genera videos con subtítulos quemados y audio TTS opcional
"""

import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Callable, List, Dict, Optional
import logging

from backend.utils.media import probe_duration

logger = logging.getLogger(__name__)


def burn_subtitles_to_video(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    subtitle_style: Optional[Dict] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
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
    
    # Escapar el path del SRT para el filtergraph de FFmpeg:
    # los dos puntos y las comillas simples son metacaracteres en este contexto.
    srt_escaped = str(srt_path).replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
    subtitle_filter = (
        f"subtitles='{srt_escaped}':force_style='"
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
    
    duration = probe_duration(video_path)

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", subtitle_filter,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-progress", "pipe:1",  # progreso real a stdout
        "-nostats",
        "-y",
        str(output_path),
    ]

    logger.info("Quemando subtitulos en video (FFmpeg)...")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    # Drenar stderr en hilo paralelo para evitar deadlock en el pipe
    stderr_buf: list[str] = []

    def _drain_stderr() -> None:
        for line in proc.stderr:
            stderr_buf.append(line)
        proc.stderr.close()

    t = threading.Thread(target=_drain_stderr, daemon=True)
    t.start()

    for line in proc.stdout:
        line = line.strip()
        if line.startswith("out_time_ms=") and duration > 0 and progress_callback:
            try:
                ms_str = line.split("=")[1].strip()
                if ms_str and ms_str != "N/A":
                    ms = int(ms_str)
                    if ms > 0:
                        progress_callback(min(0.95, ms / 1_000_000 / duration))
            except (ValueError, IndexError):
                pass

    proc.stdout.close()
    proc.wait()
    t.join(timeout=2)

    if proc.returncode != 0:
        err = "".join(stderr_buf[-20:])
        logger.error(f"Error en FFmpeg: {err}")
        raise subprocess.CalledProcessError(proc.returncode, cmd, stderr=err)

    logger.info(f"✓ Subtitulos quemados: {output_path}")
    if progress_callback:
        progress_callback(1.0)

    return output_path


async def generate_tts_audio(
    segments: List[Dict],
    output_path: Path,
    voice: str = "es-ES-AlvaroNeural",
    rate: str = "+0%",
) -> Path:
    """
    Genera audio TTS sincronizado con los timestamps de los segmentos.

    Sincronización:
    1. Consolidar: el DP grouper asigna la misma traducción a todos los
       segmentos de un grupo — sin fusionar, la voz repetiría cada oración
       una vez por segmento.
    2. Generar cada clip con edge-tts (paralelo, semáforo de 5).
    3. Ajustar cada clip a EXACTAMENTE la duración de su intervalo
       (atempo si el español es más largo, silencio de relleno si es más
       corto) — así el timeline es exacto en cada frontera y no hay deriva
       acumulada con los subtítulos.
    4. Concatenar clips + silencios de los huecos entre frases.
    """
    from backend.export.srt_exporter import consolidate_segments

    try:
        import edge_tts
    except ImportError:
        logger.error("edge-tts no está instalado. Ejecuta: pip install edge-tts")
        raise

    temp_dir = output_path.parent / "temp_tts"
    temp_dir.mkdir(exist_ok=True)

    # Fusiona segmentos consecutivos con la misma traducción (sin dividir:
    # max_duration_s enorme desactiva el split, que solo aplica a subtítulos)
    merged = consolidate_segments(segments, use_translation=True, max_duration_s=float("inf"))
    logger.info(f"Generando TTS: {len(segments)} segmentos → {len(merged)} frases")

    semaphore = asyncio.Semaphore(5)  # máx 5 conexiones simultáneas a edge-tts

    async def _gen_one(i: int, seg: dict) -> Optional[Dict]:
        text = seg.get("translated_text", seg.get("text", "")).strip()
        target_dur = float(seg.get("end", 0)) - float(seg.get("start", 0))
        if not text or target_dur <= 0.05:
            return None

        raw_file = temp_dir / f"raw_{i:04d}.mp3"
        fit_file = temp_dir / f"fit_{i:04d}.mp3"

        # Un clip fallido (red, edge-tts) no debe tumbar el export completo
        # cuando el video ya está quemado: su intervalo queda en silencio.
        try:
            async with semaphore:
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(str(raw_file))

            await asyncio.to_thread(_fit_clip_to_duration, raw_file, fit_file, target_dur)
        except Exception as e:
            logger.warning(f"Clip TTS {i} falló ({e}) — su intervalo quedará en silencio")
            return None

        return {
            "file": fit_file,
            "start": float(seg.get("start", 0)),
            "end": float(seg.get("end", 0)),
        }

    try:
        results = await asyncio.gather(*[_gen_one(i, seg) for i, seg in enumerate(merged)])
        segment_files = [r for r in results if r is not None]

        logger.info(f"✓ {len(segment_files)} frases TTS generadas y ajustadas al timeline")

        await merge_tts_segments(segment_files, output_path, temp_dir)
    finally:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    return output_path


def _fit_clip_to_duration(in_path: Path, out_path: Path, target_dur: float) -> None:
    """
    Reencoda un clip TTS para que dure EXACTAMENTE target_dur segundos.

    - Si el clip es más largo: se acelera con atempo (hasta 3.4x en dos
      etapas; el español doblado suele necesitar 1.1–1.6x).
    - Si es más corto: se mantiene el ritmo natural y apad rellena con
      silencio hasta el objetivo.
    - `-t target` garantiza el corte exacto en ambos casos.

    Salida en el mismo formato que generate_silence (MP3 24kHz mono) para
    que el concat con -c copy no corrompa timestamps.
    """
    actual = probe_duration(in_path)

    filters = []
    if actual > target_dur > 0:
        tempo = min(actual / target_dur, 3.4)
        if tempo > 2.0:  # atempo acepta [0.5, 2.0] por instancia — encadenar
            filters.extend(["atempo=2.0", f"atempo={tempo / 2.0:.4f}"])
        else:
            filters.append(f"atempo={tempo:.4f}")
    filters.append("apad")

    cmd = [
        "ffmpeg", "-i", str(in_path),
        "-filter:a", ",".join(filters),
        "-t", f"{target_dur:.3f}",
        "-ar", "24000", "-ac", "1", "-b:a", "48k",
        "-y", str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _ffconcat_path(p: Path) -> str:
    """Escapa un path para el formato ffconcat (comillas simples, barras hacia adelante)."""
    return str(p).replace("\\", "/").replace("'", "'\\''")


async def merge_tts_segments(segment_files: List[Dict], output_path: Path, temp_dir: Path) -> None:
    """Combina segmentos TTS con silencios para sincronizar con timestamps."""
    concat_file = temp_dir / "concat_list.txt"

    with open(concat_file, "w", encoding="utf-8") as f:
        last_end = 0.0
        for seg in segment_files:
            gap = seg["start"] - last_end
            if gap > 0.1:
                silence_file = temp_dir / f"silence_{last_end:.2f}.mp3"
                await generate_silence(silence_file, gap)
                f.write(f"file '{_ffconcat_path(silence_file)}'\n")
            f.write(f"file '{_ffconcat_path(seg['file'])}'\n")
            last_end = seg["end"]

    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", "-y", str(output_path),
    ]
    await asyncio.to_thread(subprocess.run, cmd, capture_output=True, check=True)


async def generate_silence(output_path: Path, duration: float) -> None:
    """
    Genera un archivo de audio silencioso sin bloquear el event loop.

    El formato debe coincidir con el output de edge-tts (MP3 24kHz mono):
    el concat posterior usa -c copy, y mezclar sample rates/canales distintos
    produce timestamps corruptos y audio desincronizado.
    """
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"anullsrc=r=24000:cl=mono:d={duration}",
        "-b:a", "48k",
        "-y",
        str(output_path),
    ]
    await asyncio.to_thread(subprocess.run, cmd, capture_output=True, check=True)


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
        "-c:v", "copy",   # Copiar video (ya tiene subtítulos)
        "-c:a", "aac",    # Encodear audio a AAC
        "-map", "0:v:0",  # Video del primer input
        "-map", "1:a:0",  # Audio del segundo input
        # apad extiende el audio con silencio indefinidamente y -shortest
        # corta en el fin del VIDEO: sin apad, un TTS más corto que el video
        # truncaría el video entero.
        "-af", "apad",
        "-shortest",
        "-y",
        str(output_path)
    ]
    
    logger.info("Reemplazando audio del video con TTS...")
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Audio reemplazado: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error reemplazando audio: {e.stderr}")
        raise
