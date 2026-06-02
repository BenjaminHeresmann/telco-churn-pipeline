"""Etapa 2 del pipeline: Limpieza y transformacion.

Convierte el CSV crudo en un dataset normalizado y enriquecido:
- TotalCharges pasa de string con celdas vacias a float con NaN.
- Yes/No de columnas binarias claras se convierten a booleano.
- Se crea la feature derivada tenure_group.
- Se eliminan duplicados.

NO valida tipos ni reglas: eso es responsabilidad de la etapa 3.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from utils.logger import get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_CLEAN = PROJECT_ROOT / "data" / "clean"

COLUMNAS_BOOLEAN_DIRECTAS = ["Partner", "Dependents", "PhoneService", "PaperlessBilling", "Churn"]

log = get_logger("limpieza")


def _ultimo_raw() -> Path:
    archivos = sorted(DATA_RAW.glob("telco_churn_raw_*.csv"))
    if not archivos:
        raise FileNotFoundError(
            f"No hay archivos crudos en {DATA_RAW}. Ejecuta primero la ingesta."
        )
    return archivos[-1]


def _categorizar_tenure(meses: int) -> str:
    if meses <= 12:
        return "0-12"
    if meses <= 24:
        return "13-24"
    if meses <= 48:
        return "25-48"
    if meses <= 72:
        return "49-72"
    return "73+"


def limpiar(ruta_raw: Path | None = None) -> tuple[Path, dict]:
    """Aplica limpieza y transformacion.

    Devuelve (ruta_csv_limpio, detalles) con archivo de entrada/salida,
    filas antes/despues y las transformaciones aplicadas.
    """
    ruta_raw = ruta_raw or _ultimo_raw()
    log.info("Iniciando limpieza desde %s", ruta_raw.name)

    df = pd.read_csv(ruta_raw)
    n_inicial = len(df)

    df.columns = df.columns.str.strip()

    nulos_total_charges = (df["TotalCharges"].astype(str).str.strip() == "").sum()
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    log.info(
        "TotalCharges: %d celdas vacias convertidas a NaN", nulos_total_charges
    )

    mask_imputable = df["TotalCharges"].isna() & (df["tenure"] == 0)
    n_imputados = int(mask_imputable.sum())
    df.loc[mask_imputable, "TotalCharges"] = 0.0
    if n_imputados:
        log.info(
            "TotalCharges: %d NaN imputados con 0 para clientes con tenure=0 (recien registrados)",
            n_imputados,
        )

    for col in COLUMNAS_BOOLEAN_DIRECTAS:
        df[col] = df[col].map({"Yes": True, "No": False})

    duplicados = df.duplicated(subset=["customerID"]).sum()
    if duplicados:
        log.warning("Encontrados %d customerID duplicados, removiendo", duplicados)
        df = df.drop_duplicates(subset=["customerID"], keep="first")

    df["tenure_group"] = df["tenure"].apply(_categorizar_tenure)

    n_final = len(df)
    log.info(
        "Limpieza completada | filas=%d -> %d | nulos=%d | duplicados=%d",
        n_inicial, n_final, df.isna().sum().sum(), duplicados,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_destino = DATA_CLEAN / f"telco_churn_clean_{timestamp}.csv"
    DATA_CLEAN.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta_destino, index=False)
    log.info("Archivo limpio guardado en %s", ruta_destino.name)

    detalles = {
        "archivo_entrada": ruta_raw.name,
        "archivo_salida": ruta_destino.name,
        "filas_entrada": int(n_inicial),
        "filas_salida": int(n_final),
        "duplicados_eliminados": int(duplicados),
        "totalcharges_vacios": int(nulos_total_charges),
        "imputados_tenure0": int(n_imputados),
        "transformaciones": [
            "TotalCharges -> numerico",
            "Yes/No -> booleano",
            "tenure_group (feature derivada)",
            "dedup por customerID",
        ],
    }
    return ruta_destino, detalles


if __name__ == "__main__":
    try:
        ruta, det = limpiar()
        log.info("OK limpieza. Archivo disponible en %s | %s", ruta, det)
        sys.exit(0)
    except Exception as exc:
        log.error("Fallo en limpieza: %s", exc, exc_info=True)
        sys.exit(1)
