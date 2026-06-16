"""
Mutex global para serializar acceso a GPU (Whisper y NLLB).
Módulo separado para evitar imports circulares entre main.py y websocket.
"""
import asyncio

gpu_lock = asyncio.Lock()
