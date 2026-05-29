"""Etapa 4 del pipeline: Carga a PostgreSQL.

Inserta los registros validados en la tabla 'clientes' usando una transaccion.
Si falla algun insert por integridad, hace ROLLBACK y deja registro en
'carga_logs'. Los registros rechazados de la etapa de validacion se insertan
en 'clientes_rechazados' para auditoria de calidad.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from utils.logger import get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_VALIDATED = PROJECT_ROOT / "data" / "validated"
DATA_REJECTED = PROJECT_ROOT / "data" / "rejected"

log = get_logger("carga_bd")


MAPEO_COLUMNAS = {
    "customerID": "customer_id",
    "gender": "gender",
    "SeniorCitizen": "senior_citizen",
    "Partner": "partner",
    "Dependents": "dependents",
    "tenure": "tenure",
    "PhoneService": "phone_service",
    "MultipleLines": "multiple_lines",
    "InternetService": "internet_service",
    "OnlineSecurity": "online_security",
    "OnlineBackup": "online_backup",
    "DeviceProtection": "device_protection",
    "TechSupport": "tech_support",
    "StreamingTV": "streaming_tv",
    "StreamingMovies": "streaming_movies",
    "Contract": "contract",
    "PaperlessBilling": "paperless_billing",
    "PaymentMethod": "payment_method",
    "MonthlyCharges": "monthly_charges",
    "TotalCharges": "total_charges",
    "tenure_group": "tenure_group",
    "Churn": "churn",
}


def _build_engine() -> Engine:
    """Construye el engine SQLAlchemy.

    Prioriza DATABASE_URL (recomendado para Supabase y Railway).
    Si no esta seteado, ensambla la URL desde variables individuales.
    Fuerza sslmode=require para conexiones a Supabase.
    """
    load_dotenv(PROJECT_ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+psycopg2://", 1
            )
        return create_engine(database_url, future=True, pool_pre_ping=True)

    user = os.getenv("POSTGRES_USER", "postgres")
    pwd = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "postgres")
    sslmode = os.getenv("POSTGRES_SSLMODE", "require")
    url = (
        f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
        f"?sslmode={sslmode}"
    )
    return create_engine(url, future=True, pool_pre_ping=True)


def _ultimo_validado() -> Path:
    archivos = sorted(DATA_VALIDATED.glob("telco_churn_valid_*.csv"))
    if not archivos:
        raise FileNotFoundError(
            f"No hay archivos validados en {DATA_VALIDATED}. Ejecuta primero la validacion."
        )
    return archivos[-1]


def _ultimo_rechazado() -> Path | None:
    archivos = sorted(DATA_REJECTED.glob("telco_churn_rechazados_*.csv"))
    return archivos[-1] if archivos else None


def _registrar_log(engine: Engine, **kwargs) -> None:
    insert = text("""
        INSERT INTO carga_logs (
            archivo_origen, registros_leidos, registros_insertados,
            registros_rechazados, duracion_segundos, estado, detalle_errores
        ) VALUES (
            :archivo, :leidos, :insertados, :rechazados, :duracion, :estado, :detalle
        )
    """)
    with engine.begin() as conn:
        conn.execute(insert, kwargs)


def cargar(ruta_validados: Path | None = None) -> dict:
    """Inserta los validados en Postgres y registra auditoria. Devuelve KPIs."""
    inicio = time.perf_counter()
    ruta_validados = ruta_validados or _ultimo_validado()
    log.info("Iniciando carga a BD desde %s", ruta_validados.name)

    df = pd.read_csv(ruta_validados)
    n_leidos = len(df)
    df = df.rename(columns=MAPEO_COLUMNAS)

    engine = _build_engine()

    n_insertados = 0
    estado = "OK"
    detalle_errores = None
    try:
        # Carga full-refresh idempotente: se vacia la tabla de estado antes de
        # insertar, de modo que reejecutar el pipeline produzca el mismo
        # resultado (principio DataOps de reproducibilidad). El historico de
        # auditoria (carga_logs) NUNCA se trunca. TRUNCATE + INSERT van en la
        # misma transaccion: si el insert falla, ROLLBACK deja la tabla intacta.
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE clientes RESTART IDENTITY CASCADE"))
            conn.execute(text("TRUNCATE TABLE clientes_rechazados RESTART IDENTITY"))
            log.info("Tablas de estado vaciadas (full-refresh)")
            df.to_sql("clientes", conn, if_exists="append", index=False, method="multi", chunksize=500)
            n_insertados = n_leidos
            log.info("Insertados %d registros en clientes", n_insertados)
    except SQLAlchemyError as err:
        estado = "ERROR"
        detalle_errores = str(err)[:1000]
        log.error("Fallo carga principal: %s", err)

    ruta_rechazados = _ultimo_rechazado()
    n_rechazados = 0
    if ruta_rechazados is not None:
        try:
            df_rech = pd.read_csv(ruta_rechazados)
            n_rechazados = len(df_rech)
            registros = []
            for _, row in df_rech.iterrows():
                payload = {k: (None if pd.isna(v) else v) for k, v in row.items()
                           if k not in ("motivo_rechazo", "tipo_validacion")}
                registros.append({
                    "customer_id": row.get("customerID"),
                    "payload": json.dumps(payload, default=str),
                    "motivo": row["motivo_rechazo"],
                    "tipo": row["tipo_validacion"],
                })
            insert_rech = text("""
                INSERT INTO clientes_rechazados (customer_id, payload, motivo_rechazo, tipo_validacion)
                VALUES (:customer_id, CAST(:payload AS JSONB), :motivo, :tipo)
            """)
            with engine.begin() as conn:
                conn.execute(insert_rech, registros)
            log.info("Auditados %d rechazados en clientes_rechazados", n_rechazados)
        except Exception as err:
            log.warning("No se pudieron registrar rechazados: %s", err)

    duracion = round(time.perf_counter() - inicio, 3)

    _registrar_log(
        engine,
        archivo=ruta_validados.name,
        leidos=n_leidos,
        insertados=n_insertados,
        rechazados=n_rechazados,
        duracion=duracion,
        estado=estado,
        detalle=detalle_errores,
    )

    kpi = {
        "registros_leidos": n_leidos,
        "registros_insertados": n_insertados,
        "registros_rechazados_auditados": n_rechazados,
        "duracion_segundos": duracion,
        "estado": estado,
    }
    log.info("Carga completada | %s", kpi)
    return kpi


if __name__ == "__main__":
    try:
        kpis = cargar()
        log.info("OK carga BD. KPIs: %s", kpis)
        sys.exit(0)
    except Exception as exc:
        log.error("Fallo en carga BD: %s", exc, exc_info=True)
        sys.exit(1)
