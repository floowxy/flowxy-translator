"""
Main FastAPI Server - Flowxy-Translator
Backend completo con GPU optimization
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Optional

import aiofiles

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yt_dlp

# Imports locales
from backend.config import (
    BASE_DIR,
    DOWNLOADS_DIR,
    EXPORTS_DIR,
    SERVER_HOST,
    SERVER_PORT,
    CORS_ORIGINS,
    NLLB_LANG_CODES,
)
from backend.utils.logger import setup_global_logger, get_logger
from backend.utils.gpu_stats import get_gpu_stats, get_cuda_info, print_gpu_summary
from backend.utils.gpu_lock import gpu_lock as _gpu_lock
from backend.utils.timers import timer
from backend.whisper.whisper_engine import transcribe_file, preload_to_cpu as _whisper_preload
from backend.translation.nllb_engine import translate_text, translate_segments, preload_to_cpu as _nllb_preload
from backend.export.srt_exporter import create_srt, create_bilingual_srt
from backend.export.vtt_exporter import create_vtt, create_bilingual_vtt
from backend.export.transcript_export import export_json, export_txt, export_bilingual_txt

# WebSocket for real-time subtitle translation
from backend.websocket.realtime_handler import websocket_endpoint

# Setup logging
setup_global_logger(level="INFO")
logger = get_logger(__name__)

# FastAPI app
app = FastAPI(
    title="Flowxy-Translator API",
    description="Sistema de transcripción y traducción GPU-optimizado",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar frontend estático
FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ============================================
# MODELS
# ============================================
class DownloadRequest(BaseModel):
    url: str
    download_video: bool = False  # Si True, descarga video completo


class TranscribeRequest(BaseModel):
    file_name: str
    language: Optional[str] = None
    task_id: Optional[str] = None  # Frontend genera el UUID para polling de progreso


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "es"


class TranslateTranscriptRequest(BaseModel):
    file_name: str
    target_lang: str = "es"
    task_id: Optional[str] = None  # Frontend genera el UUID para polling de progreso


class ExportRequest(BaseModel):
    file_name: str
    format: str  # "srt", "vtt", "json", "txt"
    use_translation: bool = False
    bilingual: bool = False


class VideoExportRequest(BaseModel):
    file_name: str
    include_tts: bool = False
    tts_voice: str = "es-ES-AlvaroNeural"
    subtitle_style: Optional[dict] = None
    task_id: Optional[str] = None


# ============================================================
# Cache Global + Progreso de tareas
# ============================================================
transcription_cache: dict = {}
translation_cache: dict = {}

# Progreso de tareas en curso: task_id -> float (0.0 - 1.0)
_task_progress: dict[str, float] = {}

# _gpu_lock viene de backend.utils.gpu_lock (compartido con WebSocket handler)


# ── Helpers de persistencia en disco ────────────────────────────────

def _transcription_cache_path(file_name: str) -> Path:
    return DOWNLOADS_DIR / f"{Path(file_name).stem}_transcription.json"


def _translation_cache_path(file_name: str, lang: str) -> Path:
    return DOWNLOADS_DIR / f"{Path(file_name).stem}_translation_{lang}.json"


_MAX_CACHE = 20  # entradas máximas por caché (FIFO cuando se supera)


def _cache_put(cache: dict, key: str, value: dict) -> None:
    """Inserta en caché con cap de _MAX_CACHE entradas (FIFO)."""
    if key not in cache and len(cache) >= _MAX_CACHE:
        cache.pop(next(iter(cache)))
    cache[key] = value


def _save_to_disk(path: Path, data: dict) -> None:
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"No se pudo persistir caché en disco: {e}")


def _load_from_disk(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"No se pudo leer caché del disco: {e}")
    return None


# ============================================
# UTILIDADES
# ============================================
def _safe_filename(file_name: str) -> str:
    """Evita path traversal: solo acepta nombres de archivo simples (sin / ni ..)."""
    safe_name = Path(file_name).name
    if not safe_name or safe_name in (".", "..") or safe_name != file_name:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    return safe_name


# ============================================
# HELPERS SÍNCRONOS (para asyncio.to_thread)
# ============================================

def _ytdlp_download(ydl_opts: dict, url: str) -> tuple:
    """Ejecuta yt-dlp sincrónicamente. Llamar siempre desde asyncio.to_thread."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info, ydl.prepare_filename(info)


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Servir frontend index.html"""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/player")
async def player():
    """Servir video player page"""
    return FileResponse(FRONTEND_DIR / "player.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "version": "1.0.0",
    }


@app.get("/api/progress/{task_id}")
async def get_task_progress(task_id: str):
    """Progreso de una tarea en curso (0.0–1.0). Retorna -1 si no existe."""
    return {"task_id": task_id, "progress": _task_progress.get(task_id, -1.0)}


@app.get("/api/gpu-stats")
async def gpu_stats():
    """Obtiene estadísticas de GPU"""
    return {
        "cuda": get_cuda_info(),
        "gpu": get_gpu_stats(),
    }


@app.post("/api/download")
async def download_audio(req: DownloadRequest):
    """
    Descarga audio o video de URL (YouTube, etc) usando yt-dlp
    """
    logger.info(f"Download request: {req.url} (video={req.download_video})")
    
    try:
        # Sufijo según tipo para no colisionar entre descarga de solo-audio
        # y video completo del mismo video (si no, yt-dlp ve "{id}.webm" ya
        # existente de un tipo y omite la descarga del otro tipo).
        suffix = "video" if req.download_video else "audio"
        out_tmpl = str(DOWNLOADS_DIR / f"%(id)s_{suffix}.%(ext)s")
    
        # Progress hook para logging
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent = d.get('_percent_str', 'N/A').strip()
                    speed = d.get('_speed_str', 'N/A').strip()
                    eta = d.get('_eta_str', 'N/A').strip()
                    logger.info(f"Descargando: {percent} | Velocidad: {speed} | ETA: {eta}")
                except Exception:
                    pass  # Evitar errores de encoding
            elif d['status'] == 'finished':
                logger.info("Descarga completada, procesando...")
        
        # Configuración de yt-dlp
        if req.download_video:
            # Descargar video 1080p HD + audio (SOLO el video, no playlist)
            ydl_opts = {
                "format": "bestvideo[height<=1080][ext=webm]+bestaudio[ext=webm]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "outtmpl": out_tmpl,
                "quiet": False,
                "no_warnings": True,
                "noplaylist": True,  # NO descargar playlist completa
                "progress_hooks": [progress_hook],
                "merge_output_format": "webm",
                "postprocessors": [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'webm',
                }],
            }
        else:
            # Solo audio (SOLO el video, no playlist)
            ydl_opts = {
                "format": "bestaudio[ext=webm]/bestaudio/best",
                "outtmpl": out_tmpl,
                "quiet": False,
                "no_warnings": True,
                "noplaylist": True,  # NO descargar playlist completa
                "progress_hooks": [progress_hook],
            }
        
        # Si existe archivo de cookies, usarlo para evitar bloqueos de YouTube
        cookies_file = BASE_DIR / "cookies.txt"
        if cookies_file.exists():
            ydl_opts["cookiefile"] = str(cookies_file)
            logger.info("Usando cookies de navegador para yt-dlp")
        
        with timer("Download audio"):
            info, filename = await asyncio.to_thread(_ytdlp_download, ydl_opts, req.url)
        
        file_path = Path(filename)
        
        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Archivo descargado no encontrado"
            )
        
        logger.info(f"Downloaded: {file_path.name}")
        
        return {
            "status": "ok",
            "file_name": file_path.name,
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "size_bytes": file_path.stat().st_size,
            "media_type": "video" if req.download_video else "audio",
        }
        
    except Exception as e:
        logger.error(f"Error descargando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audio/{file_name}")
async def get_audio(file_name: str):
    """Sirve archivo de audio descargado"""
    file_path = DOWNLOADS_DIR / _safe_filename(file_name)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(file_path)


@app.get("/video/{file_name}")
async def get_video(file_name: str):
    """Sirve archivo de video descargado"""
    file_path = DOWNLOADS_DIR / _safe_filename(file_name)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(file_path, media_type="video/webm")


@app.post("/api/transcribe")
async def transcribe_endpoint(req: TranscribeRequest):
    """Transcribe archivo de audio usando Whisper (GPU). No bloquea el event loop."""
    file_name = _safe_filename(req.file_name)
    file_path = DOWNLOADS_DIR / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    cache_key = f"{file_name}_{req.language}"

    # 1. Caché en memoria
    if cache_key in transcription_cache:
        logger.info("Transcripción en caché (memoria)")
        return transcription_cache[cache_key]

    # 2. Caché en disco — sobrevive reloads del servidor
    cached = _load_from_disk(_transcription_cache_path(file_name))
    if cached:
        logger.info("Transcripción en caché (disco)")
        _cache_put(transcription_cache, cache_key, cached)
        return cached

    # 3. Transcribir
    task_id = req.task_id or str(uuid.uuid4())
    _task_progress[task_id] = 0.0

    def _progress(p: float) -> None:
        _task_progress[task_id] = p

    logger.info(f"Transcribiendo: {file_name}")
    try:
        async with _gpu_lock:
            with timer("Transcription"):
                result = await asyncio.to_thread(
                    transcribe_file, file_path, language=req.language,
                    progress_callback=_progress,
                )

        _task_progress[task_id] = 1.0
        _cache_put(transcription_cache, cache_key, result)
        _save_to_disk(_transcription_cache_path(file_name), result)

        logger.info(f"Transcripción completada: {len(result['text'])} chars")
        return result

    except Exception as e:
        logger.error(f"Error transcribiendo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _task_progress.pop(task_id, None)


@app.post("/api/translate")
async def translate_endpoint(req: TranslateRequest):
    """Traduce texto usando NLLB (GPU). Serializado con gpu_lock."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")

    logger.info(f"Translating: {req.source_lang} -> {req.target_lang}")

    try:
        async with _gpu_lock:
            with timer("Translation"):
                result = await asyncio.to_thread(
                    translate_text,
                    req.text,
                    source_lang=req.source_lang,
                    target_lang=req.target_lang,
                )

        logger.info("Translation completed")
        return result

    except Exception as e:
        logger.error(f"Error traduciendo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate-transcript")
async def translate_transcript(req: TranslateTranscriptRequest):
    """Traduce una transcripción completa por segmentos. No bloquea el event loop."""
    file_name = _safe_filename(req.file_name)

    # 1. Caché en memoria (busca cualquier transcripción del archivo)
    transcription = None
    for key in transcription_cache:
        if key.startswith(file_name + "_"):
            transcription = transcription_cache[key]

    # 2. Caché en disco si no está en memoria
    if not transcription:
        transcription = _load_from_disk(_transcription_cache_path(file_name))

    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="Transcripción no encontrada. Transcribe primero."
        )

    segments = transcription.get("segments", [])
    source_lang = transcription.get("language", "en")

    # 3. Caché de traducción en memoria
    trans_cache_key = f"{file_name}_{req.target_lang}"
    if trans_cache_key in translation_cache:
        logger.info("Traducción en caché (memoria)")
        return translation_cache[trans_cache_key]

    # 4. Caché de traducción en disco
    cached = _load_from_disk(_translation_cache_path(file_name, req.target_lang))
    if cached:
        logger.info("Traducción en caché (disco)")
        _cache_put(translation_cache, trans_cache_key, cached)
        return cached

    # 5. Traducir
    task_id = req.task_id or str(uuid.uuid4())
    _task_progress[task_id] = 0.0

    def _progress(p: float) -> None:
        _task_progress[task_id] = p

    logger.info(f"Traduciendo {len(segments)} segmentos: {source_lang} → {req.target_lang}")
    try:
        async with _gpu_lock:
            with timer("Translate segments"):
                translated_segments = await asyncio.to_thread(
                    translate_segments,
                    segments,
                    source_lang=source_lang,
                    target_lang=req.target_lang,
                    progress_callback=_progress,
                )

        _task_progress[task_id] = 1.0
        translated_text = " ".join(
            seg.get("translated_text", "") for seg in translated_segments
        )

        result = {
            "status": "ok",
            "segments": translated_segments,
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": req.target_lang,
        }
        _cache_put(translation_cache, trans_cache_key, result)
        _save_to_disk(_translation_cache_path(file_name, req.target_lang), result)

        logger.info("Traducción completada")
        return result

    except Exception as e:
        logger.error(f"Error traduciendo transcripción: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _task_progress.pop(task_id, None)


@app.post("/api/export")
async def export_endpoint(req: ExportRequest):
    """
    Exporta transcripción/traducción en formato especificado
    """
    file_name = _safe_filename(req.file_name)

    # Transcripción: memoria → disco
    transcription = next(
        (transcription_cache[k] for k in transcription_cache if k.startswith(file_name + "_")),
        None,
    )
    if not transcription:
        transcription = _load_from_disk(_transcription_cache_path(file_name))
        if transcription:
            _cache_put(transcription_cache, f"{file_name}_None", transcription)

    if transcription is None:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada")

    segments = transcription.get("segments", [])

    # Traducción: memoria → disco (prefiere español)
    translation = None
    if req.use_translation:
        translation = next(
            (translation_cache[k] for k in translation_cache if k.startswith(file_name + "_")),
            None,
        )
        if not translation:
            for lang in ["es"] + [l for l in NLLB_LANG_CODES if l != "es"]:
                cached = _load_from_disk(_translation_cache_path(file_name, lang))
                if cached:
                    translation = cached
                    _cache_put(translation_cache, f"{file_name}_{lang}", cached)
                    break
        if translation:
            segments = translation.get("segments", segments)

    # Nombre base de archivo
    base_name = Path(file_name).stem
    output_path = EXPORTS_DIR / f"{base_name}.{req.format}"
    
    try:
        if req.format == "srt":
            if req.bilingual:
                create_bilingual_srt(segments, output_path)
            else:
                create_srt(segments, output_path, use_translation=req.use_translation)
        
        elif req.format == "vtt":
            if req.bilingual:
                create_bilingual_vtt(segments, output_path)
            else:
                create_vtt(segments, output_path, use_translation=req.use_translation)
        
        elif req.format == "txt":
            text = transcription.get("text", "")
            if req.use_translation and translation and "translated_text" in translation:
                if req.bilingual:
                    export_bilingual_txt(
                        text,
                        translation.get("translated_text", ""),
                        output_path,
                        source_lang=translation.get("source_lang", "en"),
                        target_lang=translation.get("target_lang", "es"),
                    )
                else:
                    export_txt(translation.get("translated_text", ""), output_path)
            else:
                export_txt(text, output_path)
        
        elif req.format == "json":
            data = {**transcription}
            if req.use_translation and translation:
                data["translation"] = translation
            export_json(data, output_path)
        
        else:
            raise HTTPException(status_code=400, detail=f"Formato no soportado: {req.format}")
        
        logger.info(f"Exported: {output_path.name}")
        
        return {
            "status": "ok",
            "file_name": output_path.name,
            "format": req.format,
            "path": str(output_path),
        }
        
    except Exception as e:
        logger.error(f"Error exportando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/{file_name}")
async def download_export(file_name: str):
    """Descarga archivo exportado"""
    safe_name = _safe_filename(file_name)
    file_path = EXPORTS_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(file_path, filename=safe_name)


# ============================================================
# Video Export con Subtítulos Quemados + TTS
# ============================================================

@app.post("/api/export-video")
async def export_video_with_subtitles(req: VideoExportRequest):
    """
    Exporta video con subtítulos en español quemados y opcional audio TTS
    
    Proceso:
    1. Generar archivo SRT desde traducción
    2. Quemar subtítulos en video con FFmpeg
    3. (Opcional) Generar audio TTS y reemplazar
    """
    from backend.export.video_export import (
        burn_subtitles_to_video,
        generate_tts_audio,
        replace_video_audio,
    )
    
    file_name = _safe_filename(req.file_name)

    task_id = req.task_id or str(uuid.uuid4())
    _task_progress[task_id] = 0.0

    logger.info(f"Exportando video: {file_name} (TTS: {req.include_tts})")

    # Transcripción: memoria → disco (mismo patrón que el resto de endpoints)
    transcription = next(
        (transcription_cache[k] for k in transcription_cache if k.startswith(file_name + "_")),
        None,
    )
    if not transcription:
        transcription = _load_from_disk(_transcription_cache_path(file_name))
        if transcription:
            _cache_put(transcription_cache, f"{file_name}_None", transcription)

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada. Transcribe primero.")

    # Traducción: memoria → disco (prefiere español)
    translation = next(
        (translation_cache[k] for k in translation_cache if k.startswith(file_name + "_")),
        None,
    )
    if not translation:
        for lang in ["es"] + [l for l in NLLB_LANG_CODES if l != "es"]:
            cached = _load_from_disk(_translation_cache_path(file_name, lang))
            if cached:
                translation = cached
                _cache_put(translation_cache, f"{file_name}_{lang}", cached)
                break

    if not translation:
        raise HTTPException(status_code=404, detail="Traducción no encontrada. Traduce primero.")

    # Paths
    video_path = DOWNLOADS_DIR / file_name
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    # Crear directorio de exportación si no existe
    EXPORTS_DIR.mkdir(exist_ok=True)
    
    # Nombre base para archivos de salida
    base_name = video_path.stem
    
    try:
        # 1. Generar SRT consolidado:
        #    - consolidate=True: fusiona segmentos con la misma traducción en
        #      una sola entrada → sin parpadeo, sincronizado con la oración completa
        #    - 60×3: oraciones largas del DP grouper caben sin truncarse
        _task_progress[task_id] = 0.02
        srt_path = EXPORTS_DIR / f"{base_name}_es.srt"
        await asyncio.to_thread(
            create_srt, translation["segments"], srt_path, True,
            max_chars_per_line=60, max_lines=3, consolidate=True, max_duration_s=6.0,
        )
        _task_progress[task_id] = 0.05

        # 2. FFmpeg — progreso real via callback (0.05 → 0.75)
        video_with_subs = EXPORTS_DIR / f"{base_name}_subtitulado.mp4"

        def _ffmpeg_progress(p: float) -> None:
            _task_progress[task_id] = 0.05 + p * 0.70

        await asyncio.to_thread(
            burn_subtitles_to_video,
            video_path, srt_path, video_with_subs, req.subtitle_style, _ffmpeg_progress,
        )
        _task_progress[task_id] = 0.75
        final_video = video_with_subs

        # 3. (Opcional) TTS paralelo (0.75 → 1.0)
        if req.include_tts:
            logger.info("Generando audio TTS en español...")
            _task_progress[task_id] = 0.78

            tts_audio_path = EXPORTS_DIR / f"{base_name}_tts.mp3"
            await generate_tts_audio(translation["segments"], tts_audio_path, voice=req.tts_voice)
            _task_progress[task_id] = 0.93

            final_video = EXPORTS_DIR / f"{base_name}_final_con_tts.mp4"
            await asyncio.to_thread(replace_video_audio, video_with_subs, tts_audio_path, final_video)
            logger.info(f"Video con TTS generado: {final_video}")
        else:
            logger.info(f"Video con subtitulos generado: {final_video}")
        
        _task_progress[task_id] = 1.0
        return {
            "status": "ok",
            "message": "Video exportado exitosamente",
            "file_name": final_video.name,
            "file_path": f"/api/export/{final_video.name}",
            "size_bytes": final_video.stat().st_size,
            "includes_tts": req.include_tts,
        }

    except Exception as e:
        logger.error(f"Error exportando video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _task_progress.pop(task_id, None)


# ============================================================
# Subtítulos en Tiempo Real
# ============================================================
@app.get("/api/subtitles/{file_name}")
async def get_subtitles(file_name: str):
    """Subtítulos para el reproductor — incluye words para word highlighting."""
    file_name = _safe_filename(file_name)

    # 1. Memoria → 2. Disco
    transcription = next(
        (transcription_cache[k] for k in transcription_cache if k.startswith(file_name + "_")),
        None,
    )
    if not transcription:
        transcription = _load_from_disk(_transcription_cache_path(file_name))
        if transcription:
            _cache_put(transcription_cache, f"{file_name}_None", transcription)

    if not transcription:
        raise HTTPException(status_code=404, detail="Subtítulos no encontrados. Transcribe el video primero.")

    segments = transcription.get("segments", [])

    # Traducción: 1. Memoria → 2. Disco (prefiere español)
    translation = next(
        (translation_cache[k] for k in translation_cache if k.startswith(file_name + "_")),
        None,
    )
    if not translation:
        for lang in ["es"] + [l for l in NLLB_LANG_CODES if l != "es"]:
            cached = _load_from_disk(_translation_cache_path(file_name, lang))
            if cached:
                translation = cached
                _cache_put(translation_cache, f"{file_name}_{lang}", cached)
                break

    result_segments = []
    for i, seg in enumerate(segments):
        segment_data = {
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "text": seg.get("text", ""),
            "words": seg.get("words", []),  # word-level timestamps para highlighting
        }
        if translation and i < len(translation.get("segments", [])):
            segment_data["translated"] = translation["segments"][i].get("translated_text", "")
        result_segments.append(segment_data)

    return {
        "status": "ok",
        "file_name": file_name,
        "language": transcription.get("language", "unknown"),
        "segments": result_segments,
    }


# ============================================
# WEBSOCKET - REAL-TIME SUBTITLES
# ============================================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Sube un archivo de video/audio local. Alternativa a descargar de YouTube."""
    allowed = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.mp3', '.wav', '.m4a', '.ogg', '.flac'}

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")

    upload_name = Path(file.filename).name
    ext = Path(upload_name).suffix.lower()

    if not upload_name or ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext or 'sin extensión'}")

    dest = DOWNLOADS_DIR / upload_name
    logger.info(f"Subiendo archivo local: {upload_name}")

    try:
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                await f.write(chunk)
    except Exception as e:
        logger.error(f"Error subiendo archivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    media_type = "video" if ext in {".mp4", ".mkv", ".mov", ".avi", ".webm"} else "audio"
    logger.info(f"✓ Subido: {upload_name} ({dest.stat().st_size} bytes)")

    return {
        "status": "ok",
        "file_name": upload_name,
        "size_bytes": dest.stat().st_size,
        "media_type": media_type,
    }


@app.delete("/api/cache/translation/{file_name}")
async def clear_translation_cache(file_name: str):
    """Limpia solo la caché de traducción para poder retranslate con el DP mejorado."""
    safe_name = _safe_filename(file_name)
    stem = Path(safe_name).stem

    for key in [k for k in translation_cache if k.startswith(safe_name + "_")]:
        del translation_cache[key]

    for p in DOWNLOADS_DIR.glob(f"{stem}_translation_*.json"):
        p.unlink(missing_ok=True)

    logger.info(f"Caché de traducción limpiada: {safe_name}")
    return {"status": "ok", "cleared": safe_name}


@app.delete("/api/files/{file_name}")
async def delete_file(file_name: str):
    """Elimina un archivo de media, sus JSONs de caché y los exports asociados."""
    safe_name = _safe_filename(file_name)
    stem = Path(safe_name).stem

    (DOWNLOADS_DIR / safe_name).unlink(missing_ok=True)

    for p in DOWNLOADS_DIR.glob(f"{stem}_*.json"):
        p.unlink(missing_ok=True)

    for p in EXPORTS_DIR.glob(f"{stem}_*"):
        p.unlink(missing_ok=True)

    for cache in (transcription_cache, translation_cache):
        for key in [k for k in cache if k.startswith(safe_name + "_")]:
            del cache[key]

    logger.info(f"Borrado: {safe_name}")
    return {"status": "ok", "deleted": safe_name}


@app.get("/api/history")
async def get_history():
    """Lista de videos ya procesados con transcripción en disco."""
    entries = []
    for json_path in sorted(
        DOWNLOADS_DIR.glob("*_transcription.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            media_stem = json_path.stem[: -len("_transcription")]

            candidates = [
                p for p in DOWNLOADS_DIR.glob(f"{media_stem}.*")
                if p.suffix != ".json"
            ]
            if not candidates:
                continue

            media_file = candidates[0].name
            media_type = "video" if "_video" in media_file else "audio"

            translations = [
                lang for lang in NLLB_LANG_CODES
                if _translation_cache_path(media_file, lang).exists()
            ]

            entries.append({
                "file_name": media_file,
                "media_type": media_type,
                "language": data.get("language", "?"),
                "duration": data.get("duration", 0),
                "text_preview": data.get("text", "")[:120].strip(),
                "segments": len(data.get("segments", [])),
                "translations": translations,
            })
        except Exception as e:
            logger.warning(f"Error leyendo historial {json_path.name}: {e}")

    return {"entries": entries}


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """
    WebSocket endpoint for real-time subtitle translation from Chrome extension
    """
    await websocket_endpoint(websocket)


# ============================================
# STARTUP
# ============================================

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("FLOWXY-TRANSLATOR - Starting")
    logger.info("=" * 60)

    print_gpu_summary()

    DOWNLOADS_DIR.mkdir(exist_ok=True, parents=True)
    EXPORTS_DIR.mkdir(exist_ok=True, parents=True)

    logger.info(f"Server: http://{SERVER_HOST}:{SERVER_PORT}")

    # Precargar modelos en RAM para eliminar el cold-start de 30s
    logger.info("Precargando modelos en CPU RAM (sin mover a GPU)...")
    try:
        await asyncio.to_thread(_whisper_preload)
        await asyncio.to_thread(_nllb_preload)
    except Exception as e:
        logger.warning(f"Precarga parcial: {e} — los modelos cargarán en el primer request")

    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre"""
    logger.info("Shutting down Flowxy-Translator...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info",
    )
