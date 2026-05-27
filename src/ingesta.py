"""Etapa 1 del pipeline: Ingesta automatizada.

Lee el CSV fuente, lo deposita en data/raw con sello temporal y deja
trazabilidad en logs. Es el unico punto de entrada de datos crudos al sistema.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from utils.logger import get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"

log = get_logger("ingesta")


def ingestar(origen: str | None = None) -> Path:
    """Copia el CSV fuente al area raw con timestamp y devuelve la ruta destino."""
    load_dotenv(PROJECT_ROOT / ".env")

    if origen is None:
        origen = os.getenv("SOURCE_CSV_PATH")
    if not origen:
        raise ValueError(
            "Debe definirse SOURCE_CSV_PATH en .env o pasarse como argumento."
        )

    ruta_origen = Path(origen).expanduser().resolve()
    if not ruta_origen.exists():
        raise FileNotFoundError(f"No se encuentra el archivo fuente: {ruta_origen}")

    log.info("Iniciando ingesta desde %s", ruta_origen)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_destino = f"telco_churn_raw_{timestamp}.csv"
    ruta_destino = DATA_RAW / nombre_destino

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ruta_origen, ruta_destino)

    df = pd.read_csv(ruta_destino)
    n_filas, n_cols = df.shape
    log.info(
        "Ingesta completada | archivo=%s | filas=%d | columnas=%d",
        nombre_destino, n_filas, n_cols,
    )

    return ruta_destino


if __name__ == "__main__":
    try:
        ruta = ingestar()
        log.info("OK ingesta. Archivo disponible en %s", ruta)
        sys.exit(0)
    except Exception as exc:
        log.error("Fallo en ingesta: %s", exc, exc_info=True)
        sys.exit(1)
