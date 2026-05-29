"""Renderiza los diagramas del informe a PNG via mermaid.ink (sin dependencias).

Uso: python scripts/gen_diagramas.py
Genera PNGs en docs/img/ para incrustar en el informe Word/PDF.
"""
from __future__ import annotations

import base64
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

DIAGRAMAS = {
    "arquitectura": """flowchart LR
  DEV([Equipo]) -->|git push| GH
  subgraph GH["GitHub"]
    REPO[Repo + data/source]
    CI[GitHub Actions<br/>pytest CI]
  end
  GH -->|railway up| RW
  subgraph RW["Railway (computo)"]
    API[FastAPI + Docker<br/>API REST 4 etapas]
  end
  subgraph SB["Supabase (datos)"]
    DB[(PostgreSQL 17<br/>clientes / carga_logs<br/>clientes_rechazados)]
  end
  API -->|SQL + SSL| DB
  USERS([Swagger / curl / cron]) -->|HTTP REST| API
  style GH fill:#e7e7ff,stroke:#6666cc
  style RW fill:#d4e6f1,stroke:#2874a6
  style SB fill:#d5f5e3,stroke:#1e8449
""",
    "pipeline": """flowchart TB
  SRC[CSV fuente<br/>data/source - repo]:::src
  SRC --> E1
  E1[1 INGESTA<br/>copia + timestamp + log]:::e --> RAW[(data/raw)]:::d
  RAW --> E2
  E2[2 LIMPIEZA<br/>TotalCharges, booleanos,<br/>tenure_group, duplicados]:::e --> CLN[(data/clean)]:::d
  CLN --> E3
  E3[3 VALIDACION<br/>estructural pandera +<br/>semantica reglas negocio]:::e --> VAL[(data/validated)]:::ok
  E3 --> REJ[(data/rejected<br/>con motivo)]:::ko
  VAL --> E4
  E4[4 CARGA BD<br/>full-refresh idempotente<br/>transaccional + SSL]:::e --> DB[(Supabase<br/>PostgreSQL 17)]:::db
  REJ -.audita.-> DB
  classDef src fill:#fff4e6,stroke:#d68910
  classDef e fill:#d4e6f1,stroke:#2874a6
  classDef d fill:#eaf2f8,stroke:#5499c7
  classDef ok fill:#d5f5e3,stroke:#1e8449
  classDef ko fill:#fadbd8,stroke:#c0392b
  classDef db fill:#ebdef0,stroke:#8e44ad
""",
    "er": """erDiagram
  CLIENTES {
    varchar customer_id PK
    varchar gender
    int tenure
    varchar contract
    numeric monthly_charges
    numeric total_charges
    varchar tenure_group
    boolean churn
  }
  CARGA_LOGS {
    serial id PK
    timestamp fecha_ejecucion
    int registros_insertados
    int registros_rechazados
    numeric duracion_segundos
    varchar estado
  }
  CLIENTES_RECHAZADOS {
    serial id PK
    varchar customer_id
    jsonb payload
    text motivo_rechazo
    varchar tipo_validacion
  }
  CLIENTES }o..o{ CARGA_LOGS : "auditado por (logico)"
  CLIENTES_RECHAZADOS }o..o{ CARGA_LOGS : "auditado por (logico)"
""",
    "gantt": """gantt
  title Cronograma Evaluacion 2 - Pipeline Telco Churn
  dateFormat YYYY-MM-DD
  axisFormat %d-%m
  section Setup
  Repo y Docker        :done, s1, 2026-05-26, 1d
  DDL PostgreSQL       :done, s2, after s1, 1d
  section Pipeline
  Ingesta              :done, p1, after s2, 1d
  Limpieza             :done, p2, after p1, 1d
  Validacion           :done, p3, after p2, 1d
  Carga BD             :done, p4, after p3, 1d
  Orquestador y KPIs   :done, p5, after p4, 1d
  section Cloud
  Deploy Supabase+Railway :done, c1, 2026-05-29, 1d
  Auditoria y E2E         :done, c2, after c1, 1d
  section Cierre
  Informe y diagramas  :active, d1, 2026-05-30, 2d
  Slides y ensayo      :f1, 2026-06-01, 1d
  Presentacion         :crit, f2, 2026-06-02, 1d
""",
}


def render(nombre: str, code: str) -> None:
    b64 = base64.urlsafe_b64encode(code.encode()).decode()
    url = f"https://mermaid.ink/img/{b64}?type=png&bgColor=FFFFFF"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=60).read()
    destino = OUT / f"{nombre}.png"
    destino.write_bytes(data)
    print(f"  {nombre}.png  ({len(data):,} bytes)")


def main() -> None:
    print("Renderizando diagramas a docs/img/ ...")
    for nombre, code in DIAGRAMAS.items():
        try:
            render(nombre, code)
        except Exception as exc:
            print(f"  ERROR en {nombre}: {str(exc)[:150]}")
    test = OUT / "_test.png"
    if test.exists():
        test.unlink()
    print("Listo.")


if __name__ == "__main__":
    main()
