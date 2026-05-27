# Diagramas del proyecto

Estos diagramas se renderizan en GitHub directamente (Mermaid nativo). Para exportarlos como PNG ver instrucciones al final.

---

## 1. Arquitectura del pipeline (vista por capas)

```mermaid
flowchart TB
    subgraph EXT[" "]
        SRC[CSV fuente<br/>Telco Customer Churn<br/>7044 filas - 21 columnas]
    end

    subgraph ING["CAPA 1 - INGESTA"]
        I[ingesta.py<br/>copia con timestamp]
        RAW[(data/raw/<br/>telco_churn_raw_*.csv)]
    end

    subgraph CLN["CAPA 2 - LIMPIEZA Y TRANSFORMACION"]
        L[limpieza.py<br/>TotalCharges to float<br/>Yes/No to bool<br/>tenure_group derivado]
        CLEAN[(data/clean/<br/>telco_churn_clean_*.csv)]
    end

    subgraph VAL["CAPA 3 - VALIDACION"]
        V1[validacion.py<br/>estructural: pandera]
        V2[validacion.py<br/>semantica: reglas if/else]
        VALID[(data/validated/)]
        REJ[(data/rejected/<br/>con motivo de rechazo)]
    end

    subgraph LOAD["CAPA 4 - CARGA"]
        C[carga_bd.py<br/>SQLAlchemy + psycopg2<br/>transaccional]
        DB[(PostgreSQL<br/>tabla clientes<br/>tabla carga_logs<br/>tabla clientes_rechazados)]
    end

    subgraph TRANSV["CAPAS TRANSVERSALES"]
        LOG[Logger centralizado<br/>logs/pipeline_YYYYMMDD.log]
        SEC[Variables de entorno<br/>.env]
        KPI[KPIs por etapa<br/>latencia, validez, volumen]
    end

    SRC --> I --> RAW --> L --> CLEAN --> V1 --> V2
    V2 --> VALID --> C --> DB
    V2 --> REJ
    REJ --> C

    LOG -.-> I
    LOG -.-> L
    LOG -.-> V1
    LOG -.-> C
    SEC -.-> I
    SEC -.-> C
    KPI -.-> DB

    style SRC fill:#fff4e6
    style RAW fill:#e7f3ff
    style CLEAN fill:#e7f3ff
    style VALID fill:#e7ffe7
    style REJ fill:#ffe7e7
    style DB fill:#ffe7ff
```

---

## 2. Diagrama de Flujo de Datos (DFD) - Nivel 0

```mermaid
flowchart LR
    SRC([CSV Fuente<br/>Telco Churn]):::ext

    P1[1. Ingestar]:::proc
    P2[2. Limpiar y<br/>Transformar]:::proc
    P3[3. Validar]:::proc
    P4[4. Cargar a BD]:::proc

    D1[(D1: Raw)]:::store
    D2[(D2: Clean)]:::store
    D3a[(D3a: Validated)]:::store
    D3b[(D3b: Rejected)]:::store
    D4[(D4: Postgres<br/>clientes)]:::store
    D5[(D5: Postgres<br/>carga_logs)]:::store

    ANL([Analista de Datos<br/>modelo IA Eval 3]):::ext

    SRC -->|datos crudos| P1
    P1 -->|csv con timestamp| D1
    D1 --> P2
    P2 -->|datos normalizados| D2
    D2 --> P3
    P3 -->|registros validos| D3a
    P3 -->|registros invalidos + motivo| D3b
    D3a --> P4
    D3b --> P4
    P4 -->|inserts transaccionales| D4
    P4 -->|metricas ejecucion| D5
    D4 -->|consulta para entrenamiento| ANL

    classDef ext fill:#fff4e6,stroke:#d68910,stroke-width:2px
    classDef proc fill:#d4e6f1,stroke:#2874a6,stroke-width:2px
    classDef store fill:#d5f5e3,stroke:#1e8449,stroke-width:2px
```

---

## 3. Modelo Entidad-Relación de la base de datos

```mermaid
erDiagram
    CLIENTES {
        varchar customer_id PK
        varchar gender
        smallint senior_citizen
        boolean partner
        boolean dependents
        integer tenure
        boolean phone_service
        varchar multiple_lines
        varchar internet_service
        varchar online_security
        varchar online_backup
        varchar device_protection
        varchar tech_support
        varchar streaming_tv
        varchar streaming_movies
        varchar contract
        boolean paperless_billing
        varchar payment_method
        numeric monthly_charges
        numeric total_charges
        varchar tenure_group
        boolean churn
        timestamp fecha_ingesta
    }

    CARGA_LOGS {
        serial id PK
        timestamp fecha_ejecucion
        varchar archivo_origen
        integer registros_leidos
        integer registros_insertados
        integer registros_rechazados
        numeric duracion_segundos
        varchar estado
        text detalle_errores
    }

    CLIENTES_RECHAZADOS {
        serial id PK
        varchar customer_id
        jsonb payload
        text motivo_rechazo
        varchar tipo_validacion
        timestamp fecha_rechazo
    }

    CLIENTES ||..o{ CARGA_LOGS : "auditado_por"
    CLIENTES_RECHAZADOS ||..o{ CARGA_LOGS : "auditado_por"
```

> Nota: las relaciones son logicas (por fecha_ejecucion), no por FK directa. Esto simplifica la carga masiva y permite re-cargas.

---

## 4. Secuencia de ejecucion del pipeline

```mermaid
sequenceDiagram
    actor Op as Operador / Cron
    participant O as run_pipeline.py
    participant I as ingesta.py
    participant L as limpieza.py
    participant V as validacion.py
    participant C as carga_bd.py
    participant FS as Filesystem
    participant DB as PostgreSQL

    Op->>O: python src/run_pipeline.py
    O->>I: ingestar()
    I->>FS: leer CSV fuente
    I->>FS: copiar a data/raw/ con timestamp
    I-->>O: ruta_raw
    O->>L: limpiar(ruta_raw)
    L->>FS: leer raw
    L->>FS: escribir clean
    L-->>O: ruta_clean
    O->>V: validar(ruta_clean)
    V->>FS: leer clean
    V->>V: validacion estructural (pandera)
    V->>V: validacion semantica (reglas)
    V->>FS: escribir validated + rejected
    V-->>O: rutas
    O->>C: cargar(ruta_validated)
    C->>DB: connect (SSL recomendado)
    C->>DB: BEGIN
    C->>DB: INSERT INTO clientes (...)
    C->>DB: INSERT INTO clientes_rechazados (...)
    C->>DB: INSERT INTO carga_logs (...)
    C->>DB: COMMIT
    C-->>O: KPIs
    O->>Op: resumen KPIs + duracion total
```

---

## 5. Gantt / Cronograma del proyecto (3 semanas)

```mermaid
gantt
    title Cronograma Evaluacion 2 - Pipeline Telco Churn
    dateFormat YYYY-MM-DD
    axisFormat %d-%m

    section Setup
    Repo y Docker                    :done,    s1, 2026-05-26, 1d
    DDL PostgreSQL                   :done,    s2, after s1, 1d

    section Pipeline
    Etapa 1 - Ingesta                :done,    p1, after s2, 1d
    Etapa 2 - Limpieza               :done,    p2, after p1, 1d
    Etapa 3 - Validacion             :done,    p3, after p2, 1d
    Etapa 4 - Carga BD               :done,    p4, after p3, 1d
    Orquestador y KPIs               :done,    p5, after p4, 1d

    section Documentacion
    Informe tecnico                  :active,  d1, 2026-05-27, 3d
    Diagramas                        :active,  d2, 2026-05-27, 1d
    README final                     :done,    d3, 2026-05-26, 1d

    section Defensa
    Slides presentacion              :         f1, 2026-05-30, 1d
    Ensayo demo                      :         f2, after f1, 1d
    Entrega y presentacion           :crit,    f3, 2026-06-02, 1d
```

---

## Como exportar a PNG para el informe PDF

Opciones:
1. **GitHub** - sube el repo y abre `docs/diagramas.md`, GitHub renderiza Mermaid nativamente. Screenshot.
2. **Mermaid Live Editor** - copia el bloque mermaid a https://mermaid.live, exporta PNG.
3. **VS Code** - extension "Markdown Preview Mermaid Support" + screenshot.
4. **CLI** - `npm install -g @mermaid-js/mermaid-cli` y `mmdc -i diagramas.md -o arquitectura.png`.

Para el informe PDF necesitan exportar mínimo:
- Diagrama 1 (arquitectura)
- Diagrama 2 (DFD nivel 0)
- Diagrama 3 (modelo BD)
- Diagrama 5 (Gantt)
