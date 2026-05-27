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
from utils.supabase_client import descargar_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"

log = get_logger("ingesta")


def ingestar(origen: str | None = None) -> Path:
    """Obtiene el CSV fuente y lo deposita en data/raw con timestamp.

    Estrategia de fuentes (en orden de prioridad):
    1. Parametro 'origen' explicito.
    2. Variable SUPABASE_URL + SUPABASE_KEY -> descarga desde Supabase Storage.
    3. Variable SOURCE_CSV_PATH -> lee archivo local.

    Devuelve la ruta del archivo en data/raw/.
    """
    load_dotenv(PROJECT_ROOT / ".env")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_destino = f"telco_churn_raw_{timestamp}.csv"
    ruta_destino = DATA_RAW / nombre_destino
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    if origen:
        ruta_origen = Path(origen).expanduser().resolve()
        if not ruta_origen.exists():
            raise FileNotFoundError(
                f"No se encuentra el archivo fuente: {ruta_origen}"
            )
        log.info("Ingesta desde archivo local explicito: %s", ruta_origen)
        shutil.copy2(ruta_origen, ruta_destino)

    elif os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        nombre_archivo = os.getenv("SOURCE_CSV_FILENAME", "telco_churn_source.csv")
        log.info(
            "Ingesta desde Supabase Storage: bucket=%s archivo=%s",
            os.getenv("SUPABASE_BUCKET", "telco-data"), nombre_archivo,
        )
        exito = descargar_csv(nombre_archivo, ruta_destino)
        if not exito:
            raise RuntimeError(
                f"Fallo al descargar {nombre_archivo} desde Supabase Storage"
            )

    else:
        path_local = os.getenv("SOURCE_CSV_PATH")
        if not path_local:
            raise ValueError(
                "No hay fuente configurada. Setea SUPABASE_URL+SUPABASE_KEY "
                "para Storage o SOURCE_CSV_PATH para archivo local."
            )
        ruta_origen = Path(path_local).expanduser().resolve()
        if not ruta_origen.exists():
            raise FileNotFoundError(f"Archivo local no encontrado: {ruta_origen}")
        log.info("Ingesta desde archivo local (fallback): %s", ruta_origen)
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
