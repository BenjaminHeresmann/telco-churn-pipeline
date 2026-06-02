"""Orquestador del pipeline completo.

Corre las 4 etapas en orden y mide KPIs por etapa: latencia, registros
procesados y tasa de validez. Si una etapa falla, la siguiente no ejecuta.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from utils.logger import get_logger
import ingesta
import limpieza
import validacion
import carga_bd


log = get_logger("orquestador")


def main() -> int:
    inicio_total = time.perf_counter()
    kpis: dict[str, dict] = {}

    log.info("=" * 60)
    log.info("INICIO PIPELINE TELCO CHURN")
    log.info("=" * 60)

    try:
        t0 = time.perf_counter()
        ruta_raw, det = ingesta.ingestar()
        kpis["ingesta"] = {"duracion_seg": round(time.perf_counter() - t0, 3), **det}

        t0 = time.perf_counter()
        ruta_clean, det = limpieza.limpiar(ruta_raw)
        kpis["limpieza"] = {"duracion_seg": round(time.perf_counter() - t0, 3), **det}

        t0 = time.perf_counter()
        ruta_valid, ruta_rech, det = validacion.validar(ruta_clean)
        kpis["validacion"] = {"duracion_seg": round(time.perf_counter() - t0, 3), **det}

        t0 = time.perf_counter()
        kpis_carga = carga_bd.cargar(ruta_valid)
        kpis_carga["duracion_etapa_seg"] = round(time.perf_counter() - t0, 3)
        kpis["carga_bd"] = kpis_carga

    except Exception as exc:
        log.error("PIPELINE INTERRUMPIDO: %s", exc, exc_info=True)
        return 1

    duracion_total = round(time.perf_counter() - inicio_total, 3)

    log.info("=" * 60)
    log.info("FIN PIPELINE | duracion total = %s seg", duracion_total)
    log.info("=" * 60)
    log.info("RESUMEN KPIs POR ETAPA:")
    for etapa, datos in kpis.items():
        log.info("  %s -> %s", etapa, datos)

    return 0


if __name__ == "__main__":
    sys.exit(main())
