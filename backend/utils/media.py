"""
Utilidades de inspección de archivos multimedia
"""
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    """Duración del archivo con ffprobe. Rápido y soporta todos los formatos."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0
