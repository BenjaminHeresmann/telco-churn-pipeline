"""Etapa 3 del pipeline: Validacion estructural y semantica.

- Estructural: pandera valida tipos, rangos y valores permitidos por columna.
- Semantica: reglas de negocio cruzadas (ej. si InternetService=No, los
  servicios derivados deben ser 'No internet service').

Las filas que pasen ambas validaciones van a data/validated.
Las que fallen van a data/rejected con su motivo.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pandera as pa

from utils.logger import get_logger
from utils.schema import schema_clientes, validar_reglas_semanticas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = PROJECT_ROOT / "data" / "clean"
DATA_VALIDATED = PROJECT_ROOT / "data" / "validated"
DATA_REJECTED = PROJECT_ROOT / "data" / "rejected"

log = get_logger("validacion")


def _ultimo_clean() -> Path:
    archivos = sorted(DATA_CLEAN.glob("telco_churn_clean_*.csv"))
    if not archivos:
        raise FileNotFoundError(
            f"No hay archivos limpios en {DATA_CLEAN}. Ejecuta primero la limpieza."
        )
    return archivos[-1]


def _validar_estructural(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (validos, rechazados_estructural) usando pandera."""
    try:
        schema_clientes.validate(df, lazy=True)
        return df, pd.DataFrame()
    except pa.errors.SchemaErrors as err:
        log.warning("Validacion estructural detecto %d errores", len(err.failure_cases))
        indices_invalidos = err.failure_cases["index"].dropna().astype(int).unique()
        motivos = (
            err.failure_cases
            .dropna(subset=["index"])
            .assign(index=lambda d: d["index"].astype(int))
            .groupby("index")
            .apply(lambda g: "; ".join(
                f"{r['column']}={r['failure_case']} ({r['check']})"
                for _, r in g.iterrows()
            ))
            .to_dict()
        )

        mask_invalidos = df.index.isin(indices_invalidos)
        rechazados = df[mask_invalidos].copy()
        rechazados["motivo_rechazo"] = rechazados.index.map(motivos)
        rechazados["tipo_validacion"] = "estructural"

        return df[~mask_invalidos].copy(), rechazados


def _validar_semantico(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica reglas semanticas fila por fila."""
    motivos_por_fila: dict[int, list[str]] = {}
    for idx, row in df.iterrows():
        motivos = validar_reglas_semanticas(row.to_dict())
        if motivos:
            motivos_por_fila[idx] = motivos

    if not motivos_por_fila:
        return df, pd.DataFrame()

    indices_invalidos = list(motivos_por_fila.keys())
    rechazados = df.loc[indices_invalidos].copy()
    rechazados["motivo_rechazo"] = [
        "; ".join(motivos_por_fila[i]) for i in indices_invalidos
    ]
    rechazados["tipo_validacion"] = "semantica"
    log.warning("Validacion semantica rechazo %d filas", len(rechazados))

    return df.drop(indices_invalidos), rechazados


def validar(ruta_clean: Path | None = None) -> tuple[Path, Path | None]:
    """Ejecuta validacion estructural y semantica.

    Devuelve (ruta_validados, ruta_rechazados). ruta_rechazados es None si
    todo paso correctamente.
    """
    ruta_clean = ruta_clean or _ultimo_clean()
    log.info("Iniciando validacion desde %s", ruta_clean.name)

    df = pd.read_csv(ruta_clean)
    n_inicial = len(df)

    for col_bool in ["Partner", "Dependents", "PhoneService", "PaperlessBilling", "Churn"]:
        df[col_bool] = df[col_bool].astype(bool)

    validos_estr, rechazados_estr = _validar_estructural(df)
    log.info("Validacion estructural: %d ok, %d rechazados",
             len(validos_estr), len(rechazados_estr))

    validos_final, rechazados_sem = _validar_semantico(validos_estr)
    log.info("Validacion semantica:  %d ok, %d rechazados",
             len(validos_final), len(rechazados_sem))

    rechazados_total = pd.concat([rechazados_estr, rechazados_sem], ignore_index=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    DATA_VALIDATED.mkdir(parents=True, exist_ok=True)
    ruta_validados = DATA_VALIDATED / f"telco_churn_valid_{timestamp}.csv"
    validos_final.to_csv(ruta_validados, index=False)

    ruta_rechazados: Path | None = None
    if not rechazados_total.empty:
        DATA_REJECTED.mkdir(parents=True, exist_ok=True)
        ruta_rechazados = DATA_REJECTED / f"telco_churn_rechazados_{timestamp}.csv"
        rechazados_total.to_csv(ruta_rechazados, index=False)
        log.info("Rechazados guardados en %s", ruta_rechazados.name)

    pct_ok = (len(validos_final) / n_inicial * 100) if n_inicial else 0
    log.info(
        "Validacion completada | total=%d | validos=%d (%.2f%%) | rechazados=%d",
        n_inicial, len(validos_final), pct_ok, len(rechazados_total),
    )

    return ruta_validados, ruta_rechazados


if __name__ == "__main__":
    try:
        ruta_ok, ruta_ko = validar()
        log.info("OK validacion. Validados=%s, Rechazados=%s", ruta_ok, ruta_ko)
        sys.exit(0)
    except Exception as exc:
        log.error("Fallo en validacion: %s", exc, exc_info=True)
        sys.exit(1)
