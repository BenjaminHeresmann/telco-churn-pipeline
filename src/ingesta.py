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
# Dataset fuente versionado en el repo (fallback por defecto, viaja en la imagen Docker)
DATA_SOURCE_DEFAULT = PROJECT_ROOT / "data" / "source" / "telco_churn_source.csv"

log = get_logger("ingesta")


def _rel(ruta: Path) -> str:
    """Ruta relativa al repo (posix) para mostrar de donde viene / va el archivo."""
    try:
        return ruta.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return ruta.as_posix()


def ingestar(origen: str | None = None) -> tuple[Path, dict]:
    """Obtiene el CSV fuente y lo deposita en data/raw con timestamp.

    Estrategia de fuentes (en orden de prioridad):
    1. Parametro 'origen' explicito.
    2. Variable SUPABASE_URL + SUPABASE_KEY -> descarga desde Supabase Storage.
    3. Variable SOURCE_CSV_PATH -> lee archivo local en ruta indicada.
    4. Fallback: data/source/telco_churn_source.csv versionado en el repo.

    Devuelve (ruta_del_archivo_en_data_raw, detalles) donde detalles describe
    el origen, el archivo de salida y el tamano del dataset.
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
        origen_tipo, archivo_entrada, ruta_entrada = "ruta explicita", ruta_origen.name, _rel(ruta_origen)

    elif os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        nombre_archivo = os.getenv("SOURCE_CSV_FILENAME", "telco_churn_source.csv")
        bucket = os.getenv("SUPABASE_BUCKET", "telco-data")
        log.info(
            "Ingesta desde Supabase Storage: bucket=%s archivo=%s",
            bucket, nombre_archivo,
        )
        exito = descargar_csv(nombre_archivo, ruta_destino)
        if not exito:
            raise RuntimeError(
                f"Fallo al descargar {nombre_archivo} desde Supabase Storage"
            )
        origen_tipo, archivo_entrada = "Supabase Storage", nombre_archivo
        ruta_entrada = f"Supabase Storage: {bucket}/{nombre_archivo}"

    else:
        path_local = os.getenv("SOURCE_CSV_PATH")
        if path_local:
            ruta_origen = Path(path_local).expanduser().resolve()
            origen_tipo = "ruta local (SOURCE_CSV_PATH)"
            log.info("Ingesta desde SOURCE_CSV_PATH: %s", ruta_origen)
        else:
            ruta_origen = DATA_SOURCE_DEFAULT
            origen_tipo = "repo (dataset versionado)"
            log.info("Ingesta desde dataset versionado en repo: %s", ruta_origen)
        if not ruta_origen.exists():
            raise FileNotFoundError(
                f"Archivo fuente no encontrado: {ruta_origen}. "
                "Verifica data/source/telco_churn_source.csv o setea SOURCE_CSV_PATH."
            )
        shutil.copy2(ruta_origen, ruta_destino)
        archivo_entrada, ruta_entrada = ruta_origen.name, _rel(ruta_origen)

    df = pd.read_csv(ruta_destino)
    n_filas, n_cols = df.shape
    log.info(
        "Ingesta completada | archivo=%s | filas=%d | columnas=%d",
        nombre_destino, n_filas, n_cols,
    )

    detalles = {
        "archivo_entrada": archivo_entrada,
        "ruta_entrada": ruta_entrada,
        "origen": origen_tipo,
        "archivo_salida": nombre_destino,
        "ruta_salida": _rel(ruta_destino),
        "filas": int(n_filas),
        "columnas": int(n_cols),
    }
    return ruta_destino, detalles


if __name__ == "__main__":
    try:
        ruta, det = ingestar()
        log.info("OK ingesta. Archivo disponible en %s | %s", ruta, det)
        sys.exit(0)
    except Exception as exc:
        log.error("Fallo en ingesta: %s", exc, exc_info=True)
        sys.exit(1)
