"""
Main FastAPI Server - Flowxy-Translator
Backend completo con GPU optimization
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
)
from backend.utils.logger import setup_global_logger, get_logger
from backend.utils.gpu_stats import get_gpu_stats, get_cuda_info, print_gpu_summary
from backend.utils.timers import timer
from backend.whisper.whisper_engine import transcribe_file
from backend.translation.nllb_engine import translate_text, translate_segments
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


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "es"


class TranslateTranscriptRequest(BaseModel):
    file_name: str
    target_lang: str = "es"


class ExportRequest(BaseModel):
    file_name: str
    format: str  # "srt", "vtt", "json", "txt"
    use_translation: bool = False
    bilingual: bool = False


class VideoExportRequest(BaseModel):
    file_name: str
    include_tts: bool = False
    tts_voice: str = "es-ES-AlvaroNeural"  # Voz masculina por defecto
    subtitle_style: Optional[dict] = None


# ============================================================
# Cache Global
# ============================================================
# Cache simple de transcripciones y traducciones
transcription_cache = {}
translation_cache = {}


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


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "version": "1.0.0",
    }


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
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(req.url, download=True)
                filename = ydl.prepare_filename(info)
        
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
    """
    Transcribe archivo de audio usando Whisper (GPU)
    """
    file_name = _safe_filename(req.file_name)
    file_path = DOWNLOADS_DIR / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Check cache
    cache_key = f"{file_name}_{req.language}"
    if cache_key in transcription_cache:
        logger.info("Usando transcripcion en cache")
        return transcription_cache[cache_key]

    logger.info(f"Transcribing: {file_name}")
    
    try:
        with timer("Transcription"):
            result = transcribe_file(file_path, language=req.language)
        
        # Cache result
        transcription_cache[cache_key] = result
        
        logger.info(f"Transcription completed: {len(result['text'])} chars")
        return result
        
    except Exception as e:
        logger.error(f"Error transcribiendo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate")
async def translate_endpoint(req: TranslateRequest):
    """
    Traduce texto usando NLLB (GPU)
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")
    
    logger.info(f"Translating: {req.source_lang} -> {req.target_lang}")
    
    try:
        with timer("Translation"):
            result = translate_text(
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
    """
    Traduce una transcripción completa (por segmentos)
    """
    file_name = _safe_filename(req.file_name)

    # Buscar transcripción en cache (puede tener cualquier idioma)
    transcription = None
    cache_key = None

    # Buscar por nombre de archivo (con cualquier idioma).
    # Si hay varias (re-transcripciones), usar la más reciente.
    for key in transcription_cache:
        if key.startswith(file_name + "_"):
            cache_key = key
            transcription = transcription_cache[key]
    
    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="Transcripción no encontrada. Transcribe primero."
        )
    
    segments = transcription.get("segments", [])
    source_lang = transcription.get("language", "en")
    
    logger.info(f"Translating transcript: {len(segments)} segments")
    
    try:
        with timer("Translate segments"):
            translated_segments = translate_segments(
                segments,
                source_lang=source_lang,
                target_lang=req.target_lang,
            )
        
        # Texto completo traducido
        translated_text = " ".join(
            seg.get("translated_text", "")
            for seg in translated_segments
        )
        
        # Cache result
        trans_cache_key = f"{file_name}_{req.target_lang}"
        translation_cache[trans_cache_key] = {
            "status": "ok",
            "segments": translated_segments,
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": req.target_lang,
        }
        
        logger.info("Translation completed")
        return translation_cache[trans_cache_key]
        
    except Exception as e:
        logger.error(f"Error traduciendo transcripción: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
async def export_endpoint(req: ExportRequest):
    """
    Exporta transcripción/traducción en formato especificado
    """
    file_name = _safe_filename(req.file_name)

    # Obtener transcripción (cacheada como "{file_name}_{language}",
    # donde language puede ser "None" o el idioma elegido por el usuario)
    transcription = None
    for key in transcription_cache:
        if key.startswith(file_name + "_"):
            transcription = transcription_cache[key]

    if transcription is None:
        raise HTTPException(
            status_code=404,
            detail="Transcripción no encontrada"
        )

    segments = transcription.get("segments", [])

    # Si usa traducción, obtenerla (la más reciente si hay varias)
    translation = None
    if req.use_translation:
        for key in translation_cache:
            if key.startswith(file_name + "_"):
                translation = translation_cache[key]
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
        generate_srt_file,
        burn_subtitles_to_video,
        generate_tts_audio,
        replace_video_audio
    )
    
    file_name = _safe_filename(req.file_name)

    logger.info(f"Exportando video: {file_name} (TTS: {req.include_tts})")

    # Buscar transcripción y traducción en cache
    transcription = None
    translation = None

    for key in transcription_cache:
        if key.startswith(file_name + "_"):
            transcription = transcription_cache[key]

    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="Transcripción no encontrada. Transcribe primero."
        )

    # Buscar traducción (la más reciente si hay varias)
    for key in translation_cache:
        if key.startswith(file_name + "_"):
            translation = translation_cache[key]

    if not translation:
        raise HTTPException(
            status_code=404,
            detail="Traducción no encontrada. Traduce primero."
        )

    # Paths
    video_path = DOWNLOADS_DIR / file_name
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    # Crear directorio de exportación si no existe
    EXPORTS_DIR.mkdir(exist_ok=True)
    
    # Nombre base para archivos de salida
    base_name = video_path.stem
    
    try:
        # 1. Generar SRT con traducción al español
        srt_path = EXPORTS_DIR / f"{base_name}_es.srt"
        generate_srt_file(
            translation["segments"],
            srt_path,
            use_translation=True
        )
        
        # 2. Quemar subtítulos en video
        video_with_subs = EXPORTS_DIR / f"{base_name}_subtitulado.mp4"
        burn_subtitles_to_video(
            video_path,
            srt_path,
            video_with_subs,
            subtitle_style=req.subtitle_style
        )
        
        final_video = video_with_subs
        
        # 3. (Opcional) Generar y agregar audio TTS
        if req.include_tts:
            logger.info("Generando audio TTS en español...")
            
            tts_audio_path = EXPORTS_DIR / f"{base_name}_tts.mp3"
            await generate_tts_audio(
                translation["segments"],
                tts_audio_path,
                voice=req.tts_voice
            )
            
            # Reemplazar audio
            final_video = EXPORTS_DIR / f"{base_name}_final_con_tts.mp4"
            replace_video_audio(
                video_with_subs,
                tts_audio_path,
                final_video
            )
            
            logger.info(f"Video con TTS generado: {final_video}")
        else:
            logger.info(f"Video con subtitulos generado: {final_video}")
        
        return {
            "status": "ok",
            "message": "Video exportado exitosamente",
            "file_name": final_video.name,
            "file_path": f"/api/export/{final_video.name}",
            "size_bytes": final_video.stat().st_size,
            "includes_tts": req.include_tts
        }
        
    except Exception as e:
        logger.error(f"Error exportando video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Subtítulos en Tiempo Real
# ============================================================
@app.get("/api/subtitles/{file_name}")
async def get_subtitles(file_name: str):
    """
    Obtiene subtítulos para el video player
    Retorna segmentos con timestamps y texto original/traducido
    """
    file_name = _safe_filename(file_name)

    # Buscar transcripción en cache
    transcription = None
    for key in transcription_cache:
        if key.startswith(file_name + "_"):
            transcription = transcription_cache[key]

    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="Subtítulos no encontrados. Transcribe el video primero."
        )

    segments = transcription.get("segments", [])

    # Buscar traducción si existe (la más reciente si hay varias)
    translation = None
    for key in translation_cache:
        if key.startswith(file_name + "_"):
            translation = translation_cache[key]
    
    # Combinar transcripción y traducción
    result_segments = []
    for i, seg in enumerate(segments):
        segment_data = {
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "text": seg.get("text", ""),
        }
        
        # Agregar traducción si existe
        if translation and i < len(translation.get("segments", [])):
            trans_seg = translation["segments"][i]
            segment_data["translated"] = trans_seg.get("translated_text", "")
        
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
    """Evento de inicio"""
    logger.info("=" * 60)
    logger.info("FLOWXY-TRANSLATOR - Starting")
    logger.info("=" * 60)
    
    # Print GPU info
    print_gpu_summary()
    
    # Crear directorios
    DOWNLOADS_DIR.mkdir(exist_ok=True, parents=True)
    EXPORTS_DIR.mkdir(exist_ok=True, parents=True)
    
    logger.info(f"Downloads dir: {DOWNLOADS_DIR}")
    logger.info(f"Exports dir: {EXPORTS_DIR}")
    logger.info(f"Server: http://{SERVER_HOST}:{SERVER_PORT}")
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
