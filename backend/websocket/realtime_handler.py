"""
Real-Time WebSocket Handler for Chrome Extension
Handles audio chunks from extension and returns subtitles
"""
import base64
import json
import logging
import asyncio
from typing import Dict, Any
import numpy as np

from fastapi import WebSocket, WebSocketDisconnect
from backend.utils.logger import get_logger
from backend.utils.timers import timer
from backend.whisper.whisper_engine import transcribe_array
from backend.translation.nllb_engine import translate_text

logger = get_logger(__name__)


class RealtimeHandler:
    """Handles real-time audio processing via WebSocket"""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.connection_count = 0
    
    async def handle_connection(self, websocket: WebSocket, client_id: str):
        """
        Main handler for WebSocket connection
        """
        await websocket.accept()
        logger.info(f"[WS] Client {client_id} connected")
        
        # Store connection info
        self.active_connections[client_id] = {
            "websocket": websocket,
            "target_lang": "es",
            "show_original": True,
            "audio_buffer": [],
        }
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle message
                await self.handle_message(client_id, message)
                
        except WebSocketDisconnect:
            logger.info(f"[WS] Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"[WS] Error with client {client_id}: {e}")
            await self.send_error(websocket, str(e))
        finally:
            # Cleanup
            if client_id in self.active_connections:
                del self.active_connections[client_id]
    
    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        """Process incoming message from extension"""
        msg_type = message.get("type")
        conn_info = self.active_connections[client_id]
        websocket = conn_info["websocket"]
        
        logger.debug(f"[WS] Received {msg_type} from {client_id}")
        
        if msg_type == "config":
            # Update configuration
            conn_info["target_lang"] = message.get("targetLang", "es")
            conn_info["show_original"] = message.get("showOriginal", True)
            logger.info(f"[WS] Config updated for {client_id}: {conn_info['target_lang']}")
            
            await self.send_status(websocket, "Configuration updated")
        
        elif msg_type == "audio_chunk":
            # Process audio chunk
            await self.process_audio_chunk(client_id, message)
        
        else:
            logger.warning(f"[WS] Unknown message type: {msg_type}")
    
    async def process_audio_chunk(self, client_id: str, message: Dict[str, Any]):
        """Process audio chunk and return subtitle"""
        conn_info = self.active_connections[client_id]
        websocket = conn_info["websocket"]
        
        try:
            # Decode audio data
            audio_b64 = message.get("data")
            timestamp = message.get("timestamp", 0)
            sample_rate = message.get("sample_rate", 16000)
            
            # Decode from base64
            audio_bytes = base64.b64decode(audio_b64)
            
            # Convert to numpy array (Int16 -> Float32)
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            logger.info(f"[WS] Processing {len(audio_float32)} samples at {timestamp:.2f}s")
            
            # Transcribe with Whisper (in thread pool to not block)
            with timer(f"Whisper transcription (chunk)"):
                result = await asyncio.to_thread(
                    transcribe_array,
                    audio_float32,
                    sample_rate=sample_rate
                )
            
            original_text = result.get("text", "").strip()
            
            if not original_text:
                logger.debug(f"[WS] No speech detected in chunk")
                return
            
            logger.info(f"[WS] Transcribed: '{original_text[:50]}...'")
            
            # Translate if needed
            translated_text = original_text
            target_lang = conn_info["target_lang"]
            source_lang = result.get("language", "en")
            
            if source_lang != target_lang:
                with timer(f"Translation ({source_lang} → {target_lang})"):
                    translation = await asyncio.to_thread(
                        translate_text,
                        original_text,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                    translated_text = translation.get("translated_text", original_text)
                
                logger.info(f"[WS] Translated: '{translated_text[:50]}...'")
            
            # Send subtitle back to extension
            subtitle = {
                "type": "subtitle",
                "text": translated_text,
                "original": original_text if conn_info["show_original"] else None,
                "start": timestamp,
                "end": timestamp + 2.0,  # Approximate
                "language": target_lang,
                "source_language": source_lang,
            }
            
            await websocket.send_json(subtitle)
            logger.info(f"[WS] Sent subtitle to {client_id}")
            
        except Exception as e:
            logger.error(f"[WS] Error processing audio chunk: {e}", exc_info=True)
            await self.send_error(websocket, f"Error processing audio: {str(e)}")
    
    async def send_status(self, websocket: WebSocket, message: str):
        """Send status message to client"""
        await websocket.send_json({
            "type": "status",
            "message": message
        })
    
    async def send_error(self, websocket: WebSocket, error: str):
        """Send error message to client"""
        await websocket.send_json({
            "type": "error",
            "message": error
        })


# Global handler instance
realtime_handler = RealtimeHandler()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio processing
    Path: /ws
    """
    # Generate client ID
    realtime_handler.connection_count += 1
    client_id = f"client_{realtime_handler.connection_count}"
    
    # Handle connection
    await realtime_handler.handle_connection(websocket, client_id)
