"""Cliente Supabase para descargar/subir archivos al bucket de Storage.

La etapa de ingesta usa este cliente para descargar el CSV fuente desde
Supabase Storage en lugar de leerlo del filesystem local. Esto desacopla
el dato del codigo y permite que el pipeline corra en Railway sin
necesitar volumenes compartidos.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_supabase_client():
    """Devuelve un cliente Supabase configurado, o None si no hay credenciales."""
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        return None


def descargar_csv(nombre_archivo: str, ruta_destino: Path) -> bool:
    """Descarga un CSV desde el bucket de Supabase Storage.

    Devuelve True si la descarga fue exitosa, False si no hay cliente
    o falla la descarga.
    """
    cliente = get_supabase_client()
    if cliente is None:
        return False

    bucket = os.getenv("SUPABASE_BUCKET", "telco-data")

    try:
        data = cliente.storage.from_(bucket).download(nombre_archivo)
        ruta_destino.parent.mkdir(parents=True, exist_ok=True)
        ruta_destino.write_bytes(data)
        return True
    except Exception:
        return False


def subir_csv(ruta_local: Path, nombre_destino: str) -> bool:
    """Sube un CSV local al bucket de Supabase Storage."""
    cliente = get_supabase_client()
    if cliente is None:
        return False

    bucket = os.getenv("SUPABASE_BUCKET", "telco-data")

    try:
        with open(ruta_local, "rb") as f:
            cliente.storage.from_(bucket).upload(
                nombre_destino,
                f,
                file_options={"upsert": "true"},
            )
        return True
    except Exception:
        return False
