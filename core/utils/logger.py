# core/utils/logger.py

"""
Sistema centralizado de logging para sports-predictor-advanced.

Características:
- Logs en consola (colorized)
- Logs en archivo (rotación automática)
- Niveles configurables por módulo
- Formato consistente
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


# =========================
# CONFIGURACIÓN
# =========================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

DEFAULT_LOG_LEVEL = logging.INFO
MAX_BYTES = 10 * 1024 * 1024  # 10 MB por archivo
BACKUP_COUNT = 5               # Mantener 5 archivos históricos

# Formato de logs
LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# =========================
# COLORES PARA CONSOLA (OPCIONAL)
# =========================

class ColoredFormatter(logging.Formatter):
    """
    Formatter con colores para consola (Windows/Linux compatible).
    """
    
    # Códigos ANSI para colores
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Aplicar color al nivel
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        return super().format(record)


# =========================
# SETUP LOGGER
# =========================

def setup_logger(
    name: str,
    level: int = DEFAULT_LOG_LEVEL,
    log_to_file: bool = True,
    log_to_console: bool = True,
    colored_console: bool = True
) -> logging.Logger:
    """
    Configura un logger con handlers de archivo y consola.
    
    Args:
        name: Nombre del logger (típicamente __name__ del módulo)
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Si True, escribe logs a archivo
        log_to_console: Si True, imprime logs en consola
        colored_console: Si True, usa colores en consola
    
    Returns:
        Logger configurado
    
    Ejemplo:
        logger = setup_logger(__name__)
        logger.info("Sistema iniciado")
        logger.error("Error crítico", exc_info=True)
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evitar duplicar handlers si se llama múltiples veces
    if logger.handlers:
        return logger
    
    # =========================
    # HANDLER: ARCHIVO
    # =========================
    if log_to_file:
        # Nombre de archivo basado en fecha
        log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        file_formatter = logging.Formatter(
            LOG_FORMAT,
            datefmt=DATE_FORMAT
        )
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(file_handler)
    
    # =========================
    # HANDLER: CONSOLA
    # =========================
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if colored_console:
            console_formatter = ColoredFormatter(
                LOG_FORMAT,
                datefmt=DATE_FORMAT
            )
        else:
            console_formatter = logging.Formatter(
                LOG_FORMAT,
                datefmt=DATE_FORMAT
            )
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


# =========================
# LOGGER ESPECÍFICOS
# =========================

def get_api_logger(name: str = "api") -> logging.Logger:
    """Logger para llamadas a APIs externas."""
    return setup_logger(f"api.{name}", level=logging.DEBUG)


def get_model_logger(name: str = "model") -> logging.Logger:
    """Logger para modelos (Monte Carlo, proyecciones, etc)."""
    return setup_logger(f"model.{name}", level=logging.INFO)


def get_picks_logger(name: str = "picks") -> logging.Logger:
    """Logger para generación de picks."""
    return setup_logger(f"picks.{name}", level=logging.INFO)


def get_error_logger(name: str = "error") -> logging.Logger:
    """Logger dedicado a errores críticos."""
    logger = setup_logger(f"error.{name}", level=logging.ERROR)
    
    # Handler adicional para errores críticos
    error_file = LOG_DIR / "errors.log"
    error_handler = RotatingFileHandler(
        error_file,
        maxBytes=MAX_BYTES,
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    
    error_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s\n%(pathname)s:%(lineno)d\n",
        datefmt=DATE_FORMAT
    )
    error_handler.setFormatter(error_formatter)
    
    logger.addHandler(error_handler)
    
    return logger


# =========================
# CONTEXT MANAGER
# =========================

class LogContext:
    """
    Context manager para logging de operaciones.
    
    Ejemplo:
        with LogContext("Analizando partido Yankees vs Red Sox"):
            # ... código ...
            pass
    """
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger or setup_logger("context")
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"▶ START: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"✓ DONE: {self.operation} ({duration:.2f}s)")
        else:
            self.logger.error(
                f"✗ FAILED: {self.operation} ({duration:.2f}s) - {exc_val}",
                exc_info=True
            )
        
        return False  # Re-raise exception


# =========================
# HELPERS
# =========================

def log_pick(pick: dict, logger: Optional[logging.Logger] = None):
    """
    Formatea y loggea un pick de forma legible.
    """
    if logger is None:
        logger = get_picks_logger()
    
    logger.info(
        f"PICK: {pick.get('market', 'UNKNOWN').upper()} | "
        f"{pick.get('team', 'N/A')} {pick.get('side', '').upper()} | "
        f"Odds: {pick.get('odds', 0):.2f} | "
        f"Edge: {pick.get('edge', 0)*100:.1f}% | "
        f"Confidence: {pick.get('confidence', 0)*100:.1f}%"
    )


def log_api_call(endpoint: str, params: dict, logger: Optional[logging.Logger] = None):
    """
    Loggea llamadas a APIs externas.
    """
    if logger is None:
        logger = get_api_logger()
    
    logger.debug(f"API CALL: {endpoint} | Params: {params}")


def log_error_with_context(
    error: Exception,
    context: dict,
    logger: Optional[logging.Logger] = None
):
    """
    Loggea errores con contexto adicional.
    """
    if logger is None:
        logger = get_error_logger()
    
    logger.error(
        f"ERROR: {type(error).__name__}: {error}\n"
        f"Context: {context}",
        exc_info=True
    )