"""
Sistema de logging centralizado para Flowxy-Translator
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Formato de logs
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Colores para consola (ANSI)
COLORS = {
    "DEBUG": "\033[36m",    # Cyan
    "INFO": "\033[32m",     # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",    # Red
    "CRITICAL": "\033[35m", # Magenta
    "RESET": "\033[0m",     # Reset
}


class ColoredFormatter(logging.Formatter):
    """Formatter con colores para consola"""

    def format(self, record):
        # Agregar color sin mutar permanentemente el record
        # (otros handlers, como el de archivo, también lo formatean)
        original_levelname = record.levelname
        if original_levelname in COLORS:
            record.levelname = f"{COLORS[original_levelname]}{original_levelname}{COLORS['RESET']}"

        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True,
) -> logging.Logger:
    """
    Configura un logger
    
    Args:
        name: Nombre del logger
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path al archivo de log (opcional)
        console: Si mostrar logs en consola
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Evitar duplicación de handlers
    if logger.handlers:
        return logger
    
    # Handler para consola
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Handler para archivo
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Archivo siempre guarda todo
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene o crea un logger con configuración default
    
    Args:
        name: Nombre del logger (usualmente __name__)
        
    Returns:
        Logger
    """
    return logging.getLogger(name)


# Logger global para el proyecto
def setup_global_logger(log_dir: Optional[Path] = None, level: str = "INFO"):
    """
    Configura el logger global del proyecto
    
    Args:
        log_dir: Directorio donde guardar logs
        level: Nivel de logging
    """
    log_file = None
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"flowxy-translator_{timestamp}.log"
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        root_logger.info(f"Logging to file: {log_file}")


if __name__ == "__main__":
    # Test
    logger = setup_logger("test", level="DEBUG")
    
    logger.debug("Este es un mensaje DEBUG")
    logger.info("Este es un mensaje INFO")
    logger.warning("Este es un mensaje WARNING")
    logger.error("Este es un mensaje ERROR")
    logger.critical("Este es un mensaje CRITICAL")
