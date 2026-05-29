"""Setup idempotente de Supabase: aplica el DDL y sube el CSV fuente al bucket.

Ejecutar UNA vez tras crear el proyecto en Supabase, con las variables de
entorno configuradas en .env:
    DATABASE_URL, SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET

Uso:
    python scripts/setup_supabase.py

Pasos que realiza:
1. Conecta a Supabase Postgres con SSL y ejecuta sql/01_create_tables.sql
2. Crea el bucket de Storage si no existe
3. Sube el CSV fuente del caso al bucket como telco_churn_source.csv
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = PROJECT_ROOT / "sql" / "01_create_tables.sql"
CSV_FUENTE = (
    PROJECT_ROOT.parent
    / "0.CASOS_PARCIALES_Evaluaciones-2y3"
    / "01_Telco Customer Churn"
    / "02_Base_WA_Fn-UseC_-Telco-Customer-Churn.csv"
)


def _engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("ERROR: falta DATABASE_URL en .env")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(url, future=True, pool_pre_ping=True)


def aplicar_ddl() -> None:
    print(">> Aplicando DDL en Supabase Postgres...")
    ddl = DDL_PATH.read_text(encoding="utf-8")
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(text(ddl))
    with engine.connect() as conn:
        tablas = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('clientes','carga_logs','clientes_rechazados')
            ORDER BY table_name
        """)).scalars().all()
    print(f"   Tablas creadas/verificadas: {', '.join(tablas)}")


def subir_csv() -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    bucket = os.getenv("SUPABASE_BUCKET", "telco-data")
    destino = os.getenv("SOURCE_CSV_FILENAME", "telco_churn_source.csv")

    if not url or not key:
        print(">> SUPABASE_URL/KEY no seteados, omito subida a Storage.")
        return
    if not CSV_FUENTE.exists():
        print(f">> CSV fuente no encontrado en {CSV_FUENTE}, omito subida.")
        return

    from supabase import create_client
    cliente = create_client(url, key)

    print(f">> Asegurando bucket '{bucket}'...")
    try:
        cliente.storage.create_bucket(bucket, options={"public": True})
        print(f"   Bucket '{bucket}' creado.")
    except Exception as exc:
        if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
            print(f"   Bucket '{bucket}' ya existe.")
        else:
            print(f"   Aviso al crear bucket: {exc}")

    print(f">> Subiendo {CSV_FUENTE.name} como '{destino}'...")
    with open(CSV_FUENTE, "rb") as f:
        cliente.storage.from_(bucket).upload(
            destino, f, file_options={"upsert": "true", "content-type": "text/csv"}
        )
    print(f"   CSV subido a {bucket}/{destino}.")


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    print("=" * 60)
    print("SETUP SUPABASE - Telco Churn Pipeline")
    print("=" * 60)
    try:
        aplicar_ddl()
        subir_csv()
    except Exception as exc:
        print(f"\nERROR en setup: {exc}")
        return 1
    print("\nSetup completado. Ya puedes ejecutar el pipeline:")
    print("  POST /pipeline/run  (en Railway)  o  python src/run_pipeline.py (local)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
