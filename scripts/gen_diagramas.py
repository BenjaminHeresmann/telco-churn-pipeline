"""Renderiza los diagramas del informe/slides a PNG via mermaid.ink (sin dependencias).

Uso: python scripts/gen_diagramas.py
Genera PNGs en docs/img/ con la paleta del sistema de diseno (azul #15406b,
acento #2563EB, verde #10B981, grises slate), fondo blanco para integrar en cards.
"""
from __future__ import annotations

import base64
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# Tema base coherente con el sistema de diseno de las slides/informe.
INIT = (
    "%%{init: {'theme':'base','themeVariables':{"
    "'fontFamily':'Trebuchet MS, Segoe UI, Arial',"
    "'primaryColor':'#EAF1F9','primaryBorderColor':'#15406b','primaryTextColor':'#0F172A',"
    "'lineColor':'#64748B','tertiaryColor':'#F1F5F9','clusterBkg':'#F8FAFC',"
    "'clusterBorder':'#CBD5E1'}}}%%\n"
)

DIAGRAMAS = {
    "arquitectura": INIT + """flowchart LR
  DEV([Equipo]) -->|git push| GH
  subgraph GH["GitHub"]
    REPO[Repo + data/source]
    CI[GitHub Actions<br/>pytest CI]
  end
  GH -->|railway up| RW
  subgraph RW["Railway · computo"]
    API[FastAPI + Docker<br/>API REST · 4 etapas]
  end
  subgraph SB["Supabase · datos"]
    DB[(PostgreSQL 17<br/>clientes · carga_logs<br/>clientes_rechazados)]
  end
  API -->|SQL + SSL| DB
  USERS([Swagger · curl · cron]) -->|HTTP REST| API
  style GH fill:#EEF2FB,stroke:#1D4ED8,stroke-width:1px
  style RW fill:#EAF1F9,stroke:#15406b,stroke-width:1px
  style SB fill:#E7F8F0,stroke:#10B981,stroke-width:1px
""",
    "pipeline": INIT + """flowchart TB
  SRC[CSV fuente<br/>data/source · repo]:::src
  SRC --> E1
  E1[<b>1 · INGESTA</b><br/>copia + timestamp + log]:::e --> RAW[(data/raw)]:::d
  RAW --> E2
  E2[<b>2 · LIMPIEZA</b><br/>TotalCharges · booleanos<br/>tenure_group · duplicados]:::e --> CLN[(data/clean)]:::d
  CLN --> E3
  E3[<b>3 · VALIDACION</b><br/>estructural pandera +<br/>semantica reglas negocio]:::e --> VAL[(data/validated)]:::ok
  E3 --> REJ[(data/rejected<br/>con motivo)]:::ko
  VAL --> E4
  E4[<b>4 · CARGA BD</b><br/>full-refresh idempotente<br/>transaccional + SSL]:::e --> DB[(Supabase<br/>PostgreSQL 17)]:::db
  REJ -.audita.-> DB
  classDef src fill:#FEF6E7,stroke:#D9A21B,color:#0F172A
  classDef e fill:#EAF1F9,stroke:#15406b,color:#0F172A,stroke-width:1.5px
  classDef d fill:#F1F5F9,stroke:#94A3B8,color:#334155
  classDef ok fill:#E7F8F0,stroke:#10B981,color:#0F172A
  classDef ko fill:#FDECEA,stroke:#E0533D,color:#0F172A
  classDef db fill:#EFE9FB,stroke:#7C3AED,color:#0F172A
""",
    "er": INIT + """erDiagram
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
  CLIENTES }o..o{ CARGA_LOGS : "auditado (logico)"
  CLIENTES_RECHAZADOS }o..o{ CARGA_LOGS : "auditado (logico)"
""",
    "gantt": INIT + """gantt
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
    (OUT / f"{nombre}.png").write_bytes(data)
    print(f"  {nombre}.png  ({len(data):,} bytes)")


def main() -> None:
    print("Renderizando diagramas a docs/img/ ...")
    for nombre, code in DIAGRAMAS.items():
        try:
            render(nombre, code)
        except Exception as exc:
            print(f"  ERROR en {nombre}: {str(exc)[:150]}")
    print("Listo.")


if __name__ == "__main__":
    main()
