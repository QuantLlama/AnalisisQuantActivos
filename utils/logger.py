"""
utils/logger.py — Sistema de logging estructurado para el proyecto.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.FileHandler(LOG_DIR / "analisis_activos.log", encoding="utf-8")
_file_handler.setFormatter(_FORMATTER)
_file_handler.setLevel(logging.DEBUG)

# No enviar logs a consola por defecto (la UI usa rich)
logging.basicConfig(level=logging.DEBUG, handlers=[_file_handler])


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger configurado para el módulo indicado."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_file_handler)
    logger.setLevel(logging.DEBUG)
    return logger
