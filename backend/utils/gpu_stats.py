"""
GPU Stats Monitor para Flowxy-Translator
Monitorea estadísticas de NVIDIA GPU usando pynvml
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_gpu_stats(device_index: int = 0) -> Dict[str, Any]:
    """
    Obtiene estadísticas de la GPU
    
    Args:
        device_index: Índice de la GPU (default 0)
        
    Returns:
        Dict con estadísticas de GPU o error info
    """
    try:
        import pynvml
        
        # Inicializar NVML
        pynvml.nvmlInit()
        
        # Obtener handle de la GPU
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
        
        # Obtener información
        name = pynvml.nvmlDeviceGetName(handle)
        
        # Memoria
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        mem_total = mem_info.total / (1024 ** 3)  # GB
        mem_used = mem_info.used / (1024 ** 3)  # GB
        mem_free = mem_info.free / (1024 ** 3)  # GB
        mem_percent = (mem_used / mem_total) * 100
        
        # Utilización
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_util = utilization.gpu
        mem_util = utilization.memory
        
        # Temperatura
        try:
            temperature = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
        except:
            temperature = None
        
        # Power
        try:
            power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Watts
            power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
            power_percent = (power_usage / power_limit) * 100
        except:
            power_usage = None
            power_limit = None
            power_percent = None
        
        # Cleanup
        pynvml.nvmlShutdown()
        
        return {
            "available": True,
            "device_index": device_index,
            "name": name,
            "memory": {
                "total_gb": round(mem_total, 2),
                "used_gb": round(mem_used, 2),
                "free_gb": round(mem_free, 2),
                "percent": round(mem_percent, 1),
            },
            "utilization": {
                "gpu_percent": gpu_util,
                "memory_percent": mem_util,
            },
            "temperature_c": temperature,
            "power": {
                "usage_w": round(power_usage, 1) if power_usage else None,
                "limit_w": round(power_limit, 1) if power_limit else None,
                "percent": round(power_percent, 1) if power_percent else None,
            },
        }
        
    except ImportError:
        logger.warning("pynvml no instalado. No se pueden obtener stats de GPU.")
        return {
            "available": False,
            "error": "pynvml no instalado",
        }
    except Exception as e:
        logger.error(f"Error obteniendo GPU stats: {e}")
        return {
            "available": False,
            "error": str(e),
        }


def check_cuda_available() -> bool:
    """Verifica si CUDA está disponible"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_cuda_info() -> Dict[str, Any]:
    """Obtiene información de CUDA"""
    try:
        import torch
        
        if not torch.cuda.is_available():
            return {
                "available": False,
                "message": "CUDA no está disponible",
            }
        
        return {
            "available": True,
            "version": torch.version.cuda,
            "device_count": torch.cuda.device_count(),
            "current_device": torch.cuda.current_device(),
            "device_name": torch.cuda.get_device_name(0),
            "device_capability": torch.cuda.get_device_capability(0),
        }
    except ImportError:
        return {
            "available": False,
            "error": "PyTorch no instalado",
        }


def print_gpu_summary():
    """Imprime un resumen de GPU info en consola"""
    print("\n" + "=" * 60)
    print("GPU SUMMARY - Flowxy-Translator")
    print("=" * 60)
    
    # CUDA info
    cuda_info = get_cuda_info()
    if cuda_info["available"]:
        print(f"✓ CUDA Version: {cuda_info['version']}")
        print(f"✓ Device: {cuda_info['device_name']}")
        print(f"✓ Capability: {cuda_info['device_capability']}")
    else:
        print("✗ CUDA no disponible")
        print(f"  Razón: {cuda_info.get('error', cuda_info.get('message'))}")
    
    # GPU stats
    gpu_stats = get_gpu_stats()
    if gpu_stats["available"]:
        print(f"\n✓ GPU: {gpu_stats['name']}")
        mem = gpu_stats["memory"]
        print(f"  Memory: {mem['used_gb']:.1f}/{mem['total_gb']:.1f} GB ({mem['percent']:.1f}%)")
        util = gpu_stats["utilization"]
        print(f"  Utilization: GPU {util['gpu_percent']}% | Memory {util['memory_percent']}%")
        
        if gpu_stats["temperature_c"]:
            print(f"  Temperature: {gpu_stats['temperature_c']}°C")
        
        if gpu_stats["power"]["usage_w"]:
            pwr = gpu_stats["power"]
            print(f"  Power: {pwr['usage_w']}/{pwr['limit_w']} W ({pwr['percent']:.1f}%)")
    else:
        print(f"\n✗ GPU stats no disponibles: {gpu_stats.get('error')}")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Test
    print_gpu_summary()
    
    import json
    stats = get_gpu_stats()
    print("\nJSON Output:")
    print(json.dumps(stats, indent=2))
