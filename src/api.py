"""API REST del pipeline Telco Churn.

Expone cada etapa del pipeline como un endpoint HTTP independiente, mas un
endpoint de orquestacion completa. Pensada para correr en Railway con
Supabase como BD.

Endpoints:
    GET  /                      - info de la API
    GET  /health                - health check
    POST /pipeline/run          - ejecuta las 4 etapas en orden
    POST /pipeline/ingest       - solo ingesta
    POST /pipeline/clean        - solo limpieza
    POST /pipeline/validate     - solo validacion
    POST /pipeline/load         - solo carga BD
    GET  /kpis/last             - ultimos N registros de carga_logs
    GET  /kpis/resumen          - KPIs agregados de todas las ejecuciones
    GET  /logs/last             - ultimas N lineas del log de hoy
    GET  /rechazados            - ultimos N registros rechazados con motivo
    GET  /docs                  - Swagger UI auto-generado por FastAPI
"""
from __future__ import annotations

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

import ingesta
import limpieza
import validacion
import carga_bd
from utils.logger import LOG_DIR, get_logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
log = get_logger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_dotenv(PROJECT_ROOT / ".env")
    log.info("API iniciada. Ambiente: %s", os.getenv("RAILWAY_ENVIRONMENT", "local"))
    yield
    log.info("API deteniendose.")


app = FastAPI(
    title="Telco Churn DataOps API",
    description=(
        "Pipeline DataOps desacoplado para preparacion de datos de churn. "
        "Cada etapa del pipeline es un endpoint independiente. "
        "Postgres provisto por Supabase, deploy en Railway."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
# allow_credentials=False: la API no usa cookies ni auth por sesion, y la
# combinacion allow_credentials=True + allow_origins=["*"] es invalida segun
# la especificacion CORS (los navegadores la rechazan).
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RespuestaEtapa(BaseModel):
    etapa: str
    estado: str
    duracion_segundos: float
    detalles: dict[str, Any]


class RespuestaPipeline(BaseModel):
    estado: str
    duracion_total_segundos: float
    etapas: list[RespuestaEtapa]


@app.get("/", tags=["info"])
def root():
    return {
        "service": "Telco Churn DataOps API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["info"])
def health():
    """Verifica que la API responde y que la BD esta accesible."""
    db_ok = False
    db_error = None
    try:
        engine = carga_bd._build_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_error = str(exc)[:200]

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "database_error": db_error,
        "timestamp": time.time(),
    }


@app.post("/pipeline/ingest", response_model=RespuestaEtapa, tags=["pipeline"])
def endpoint_ingest():
    t0 = time.perf_counter()
    try:
        _, det = ingesta.ingestar()
        return RespuestaEtapa(
            etapa="ingesta",
            estado="OK",
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=det,
        )
    except Exception as exc:
        log.error("Fallo ingesta: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/pipeline/clean", response_model=RespuestaEtapa, tags=["pipeline"])
def endpoint_clean():
    t0 = time.perf_counter()
    try:
        _, det = limpieza.limpiar()
        return RespuestaEtapa(
            etapa="limpieza",
            estado="OK",
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=det,
        )
    except Exception as exc:
        log.error("Fallo limpieza: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/pipeline/validate", response_model=RespuestaEtapa, tags=["pipeline"])
def endpoint_validate():
    t0 = time.perf_counter()
    try:
        _, _, det = validacion.validar()
        return RespuestaEtapa(
            etapa="validacion",
            estado="OK",
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=det,
        )
    except Exception as exc:
        log.error("Fallo validacion: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/pipeline/load", response_model=RespuestaEtapa, tags=["pipeline"])
def endpoint_load():
    t0 = time.perf_counter()
    try:
        kpis = carga_bd.cargar()
        return RespuestaEtapa(
            etapa="carga_bd",
            estado=kpis.get("estado", "OK"),
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=kpis,
        )
    except Exception as exc:
        log.error("Fallo carga BD: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/pipeline/run", response_model=RespuestaPipeline, tags=["pipeline"])
def endpoint_run_pipeline():
    """Ejecuta las 4 etapas en orden. Si una falla, detiene la cadena."""
    inicio_total = time.perf_counter()
    resultados: list[RespuestaEtapa] = []
    estado_general = "OK"

    try:
        t0 = time.perf_counter()
        ruta_raw, det = ingesta.ingestar()
        resultados.append(RespuestaEtapa(
            etapa="ingesta", estado="OK",
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=det,
        ))

        t0 = time.perf_counter()
        ruta_clean, det = limpieza.limpiar(ruta_raw)
        resultados.append(RespuestaEtapa(
            etapa="limpieza", estado="OK",
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=det,
        ))

        t0 = time.perf_counter()
        ruta_valid, ruta_rech, det = validacion.validar(ruta_clean)
        resultados.append(RespuestaEtapa(
            etapa="validacion", estado="OK",
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=det,
        ))

        t0 = time.perf_counter()
        kpis = carga_bd.cargar(ruta_valid)
        resultados.append(RespuestaEtapa(
            etapa="carga_bd", estado=kpis.get("estado", "OK"),
            duracion_segundos=round(time.perf_counter() - t0, 3),
            detalles=kpis,
        ))

    except Exception as exc:
        estado_general = "ERROR"
        log.error("Pipeline interrumpido: %s", exc, exc_info=True)
        resultados.append(RespuestaEtapa(
            etapa="error",
            estado="ERROR",
            duracion_segundos=0,
            detalles={"mensaje": str(exc)[:500]},
        ))

    return RespuestaPipeline(
        estado=estado_general,
        duracion_total_segundos=round(time.perf_counter() - inicio_total, 3),
        etapas=resultados,
    )


@app.get("/kpis/last", tags=["monitoreo"])
def kpis_ultimos(limit: int = 10):
    """Devuelve los ultimos N registros de carga_logs (auditoria del pipeline)."""
    try:
        engine = carga_bd._build_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, fecha_ejecucion, archivo_origen, registros_leidos,
                       registros_insertados, registros_rechazados,
                       duracion_segundos, estado
                FROM carga_logs
                ORDER BY fecha_ejecucion DESC
                LIMIT :lim
            """), {"lim": limit}).mappings().all()
        return {"total": len(rows), "registros": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/kpis/resumen", tags=["monitoreo"])
def kpis_resumen():
    """KPIs agregados sobre las ultimas ejecuciones."""
    try:
        engine = carga_bd._build_engine()
        with engine.connect() as conn:
            resumen = conn.execute(text("""
                SELECT
                    COUNT(*) AS total_ejecuciones,
                    SUM(registros_leidos) AS total_leidos,
                    SUM(registros_insertados) AS total_insertados,
                    SUM(registros_rechazados) AS total_rechazados,
                    AVG(duracion_segundos) AS duracion_promedio_seg,
                    MAX(fecha_ejecucion) AS ultima_ejecucion,
                    SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END) AS exitosas,
                    SUM(CASE WHEN estado = 'ERROR' THEN 1 ELSE 0 END) AS fallidas
                FROM carga_logs
            """)).mappings().first()
        return dict(resumen) if resumen else {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/logs/last", tags=["monitoreo"])
def logs_ultimos(lineas: int = 50):
    """Devuelve las ultimas N lineas del log de hoy."""
    from datetime import datetime
    archivo = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    if not archivo.exists():
        return {"archivo": archivo.name, "lineas": []}
    try:
        contenido = archivo.read_text(encoding="utf-8").splitlines()
        return {
            "archivo": archivo.name,
            "total_lineas": len(contenido),
            "lineas": contenido[-lineas:],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/rechazados", tags=["monitoreo"])
def consultar_rechazados(limit: int = 20):
    """Devuelve los ultimos N registros rechazados con sus motivos."""
    try:
        engine = carga_bd._build_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT customer_id, motivo_rechazo, tipo_validacion, fecha_rechazo
                FROM clientes_rechazados
                ORDER BY fecha_rechazo DESC
                LIMIT :lim
            """), {"lim": limit}).mappings().all()
        return {"total": len(rows), "registros": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
