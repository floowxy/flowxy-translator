"""
Detección de specs de CPU/RAM del sistema — informativas, no deciden el
preset (eso lo hace la VRAM/CUDA vía backend.presets.recommend_preset).

Sin dependencia nueva: os.sysconf cubre Linux/macOS (POSIX), ctypes cubre
Windows. Si nada aplica, se devuelve None y el frontend muestra "desconocido".
"""
import ctypes
import logging
import os
import sys

logger = logging.getLogger(__name__)


def get_cpu_cores() -> int | None:
    return os.cpu_count()


def get_ram_total_gb() -> float | None:
    try:
        if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            return round((page_size * phys_pages) / (1024 ** 3), 1)

        if sys.platform == "win32":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            return round(stat.ullTotalPhys / (1024 ** 3), 1)
    except Exception as e:
        logger.warning(f"No se pudo detectar RAM total: {e}")

    return None
