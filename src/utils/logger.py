"""Logger centralizado del pipeline.

Cada etapa obtiene un logger nombrado que escribe simultaneamente a
consola y a un archivo en logs/, con timestamp por ejecucion.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-15s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def get_logger(nombre_etapa: str) -> logging.Logger:
    """Devuelve un logger configurado para una etapa del pipeline."""
    logger = logging.getLogger(nombre_etapa)

    if logger.handlers:
        return logger

    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(nivel)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    consola = logging.StreamHandler()
    consola.setFormatter(formatter)
    logger.addHandler(consola)

    ejecucion = datetime.now().strftime("%Y%m%d")
    archivo = LOG_DIR / f"pipeline_{ejecucion}.log"
    handler_archivo = logging.FileHandler(archivo, encoding="utf-8")
    handler_archivo.setFormatter(formatter)
    logger.addHandler(handler_archivo)

    logger.propagate = False
    return logger
