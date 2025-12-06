"""
Performance Timers para medir tiempos de ejecución
"""
import time
from typing import Optional, Dict, List
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Timer:
    """Timer simple para medir tiempo de ejecución"""
    
    def __init__(self, name: str = "Timer"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: Optional[float] = None
    
    def start(self):
        """Inicia el timer"""
        self.start_time = time.perf_counter()
        return self
    
    def stop(self) -> float:
        """Detiene el timer y retorna tiempo elapsed en segundos"""
        if self.start_time is None:
            raise RuntimeError("Timer no ha sido iniciado")
        
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        return self.elapsed
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, *args):
        """Context manager exit"""
        elapsed = self.stop()
        logger.info(f"⏱️  {self.name}: {elapsed:.3f}s")


@contextmanager
def timer(name: str = "Operation", log_level: str = "INFO"):
    """
    Context manager para timing
    
    Usage:
        with timer("Mi operación"):
            # código a medir
            time.sleep(1)
    
    Args:
        name: Nombre de la operación
        log_level: Nivel de log (DEBUG, INFO, WARNING, ERROR)
    """
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    
    log_func = getattr(logger, log_level.lower())
    log_func(f"⏱️  {name}: {elapsed:.3f}s")


class StatsTimer:
    """Timer con estadísticas acumulativas"""
    
    def __init__(self, name: str = "StatsTimer"):
        self.name = name
        self.measurements: List[float] = []
        self._current_start: Optional[float] = None
    
    def start(self):
        """Inicia una medición"""
        self._current_start = time.perf_counter()
        return self
    
    def stop(self) -> float:
        """Detiene la medición actual y la agrega a stats"""
        if self._current_start is None:
            raise RuntimeError("Timer no ha sido iniciado")
        
        elapsed = time.perf_counter() - self._current_start
        self.measurements.append(elapsed)
        self._current_start = None
        return elapsed
    
    def get_stats(self) -> Dict[str, float]:
        """Obtiene estadísticas de todas las mediciones"""
        if not self.measurements:
            return {
                "count": 0,
                "total": 0.0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
            }
        
        return {
            "count": len(self.measurements),
            "total": sum(self.measurements),
            "mean": sum(self.measurements) / len(self.measurements),
            "min": min(self.measurements),
            "max": max(self.measurements),
        }
    
    def reset(self):
        """Resetea todas las mediciones"""
        self.measurements.clear()
        self._current_start = None
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, *args):
        """Context manager exit"""
        self.stop()


class TimerRegistry:
    """Registro global de timers con nombres"""
    
    def __init__(self):
        self.timers: Dict[str, StatsTimer] = {}
    
    def get_timer(self, name: str) -> StatsTimer:
        """Obtiene o crea un timer por nombre"""
        if name not in self.timers:
            self.timers[name] = StatsTimer(name)
        return self.timers[name]
    
    @contextmanager
    def time(self, name: str):
        """Context manager para timing con registro"""
        timer = self.get_timer(name)
        timer.start()
        try:
            yield timer
        finally:
            timer.stop()
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Obtiene estadísticas de todos los timers"""
        return {name: timer.get_stats() for name, timer in self.timers.items()}
    
    def print_summary(self):
        """Imprime un resumen de todos los timers"""
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        
        for name, stats in self.get_all_stats().items():
            if stats["count"] > 0:
                print(f"\n{name}:")
                print(f"  Count: {stats['count']}")
                print(f"  Total: {stats['total']:.3f}s")
                print(f"  Mean:  {stats['mean']:.3f}s")
                print(f"  Min:   {stats['min']:.3f}s")
                print(f"  Max:   {stats['max']:.3f}s")
        
        print("=" * 60 + "\n")
    
    def reset_all(self):
        """Resetea todos los timers"""
        for timer in self.timers.values():
            timer.reset()


# Instancia global
_registry = TimerRegistry()


def get_registry() -> TimerRegistry:
    """Obtiene el registro global de timers"""
    return _registry


if __name__ == "__main__":
    # Test básico
    with timer("Test 1"):
        time.sleep(0.1)
    
    # Test con stats
    stats_timer = StatsTimer("Test Stats")
    for i in range(5):
        with stats_timer:
            time.sleep(0.05)
    
    print("\nStats:")
    print(stats_timer.get_stats())
    
    # Test con registry
    registry = get_registry()
    
    for i in range(3):
        with registry.time("operacion_1"):
            time.sleep(0.1)
    
    for i in range(5):
        with registry.time("operacion_2"):
            time.sleep(0.05)
    
    registry.print_summary()
