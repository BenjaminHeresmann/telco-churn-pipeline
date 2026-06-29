# Pipeline DataOps - Telco Customer Churn (Cloud-Native)

Pipeline DataOps **desacoplado** de 4 etapas para preparar el dataset Telco Customer Churn y dejarlo cargado en PostgreSQL listo para entrenar un modelo de predicción de abandono.

**Arquitectura cloud-native:** API REST en Railway + PostgreSQL gestionado en Supabase + CI/CD vía GitHub Actions. Cero monolito, cada componente despliega y escala independientemente.

**Asignatura:** ITY1101 Gestión de Datos para IA - Duoc UC
**Evaluación:** Parcial N°2 (pipeline DataOps) + Parcial N°3 (modelo IA · BI · seguridad)
**Equipo:** Benjamín Heresmann, Diego Hernández (equipo de 2 autorizado por el docente)

> **Evaluación 3** construye sobre este pipeline: entrena un modelo de churn (recall **79,7%**), lo expone en un **dashboard BI**, audita la seguridad frente a la **Ley 21.719** y mide el rendimiento en la nube. Ver la sección [Evaluación 3](#evaluación-3-modelo-de-ia-bi-y-seguridad).

## 🚀 Desplegado y funcionando

| Recurso | URL |
|---|---|
| **API en producción (Railway)** | https://telco-api-production-e466.up.railway.app |
| **Documentación interactiva (Swagger)** | https://telco-api-production-e466.up.railway.app/docs |
| **Health check** | https://telco-api-production-e466.up.railway.app/health |
| **Presentación Eval 3 — deck (Vercel)** | https://deck-benjaminheresmanns-projects.vercel.app |
| **Presentación Eval 2 — deck (Vercel)** | https://telco-churn-defensa.vercel.app |
| **Dashboard BI (Streamlit)** | local: `streamlit run dashboard/app.py` → http://localhost:8501 |
| **Repositorio (GitHub)** | https://github.com/BenjaminHeresmann/telco-churn-pipeline |
| **Base de datos** | PostgreSQL gestionado en Supabase (proyecto `telco-churn`) |

**Probar el pipeline completo en la nube (carga 7.043 clientes en Supabase):**
```bash
curl -X POST https://telco-api-production-e466.up.railway.app/pipeline/run
```

---

## Arquitectura desacoplada

```
┌────────────────┐         ┌──────────────────────┐         ┌────────────────────┐
│  GitHub Repo   │ ──CI──► │   Railway            │ ──SQL──►│   Supabase         │
│  - Pipeline    │  Push   │   - FastAPI (Docker) │  HTTPS  │   - PostgreSQL 17  │
│  - data/source │ deploy  │   - 4 etapas pipeline│  (SSL)  │   - Dashboard SQL  │
│  - Dockerfile  │ ──────► │   - /pipeline/run    │         │   - Storage (opc.) │
│  - Actions(CI) │         │   - /kpis /logs      │         │                    │
└────────────────┘         └──────────────────────┘         └────────────────────┘
                                       │
                                       ▼
                              HTTP REST publico
                              (consumible por
                              dashboards, scripts,
                              workflows externos)
```

> **Fuente del CSV (MVP):** el dataset viaja versionado en el repo
> (`data/source/telco_churn_source.csv`) y dentro de la imagen Docker. Supabase se
> usa como **base de datos** (requisito del docente). El código además soporta
> descargar el CSV desde Supabase Storage si se configuran `SUPABASE_URL`/`KEY`,
> pero no es necesario para el MVP.

**Componentes desacoplados:**

| Componente | Rol | Servicio | Justificación |
|---|---|---|---|
| **Capa de datos** | PostgreSQL + Storage | Supabase | Postgres gestionado, SSL out-of-the-box, UI de admin, tier gratis |
| **Capa de procesamiento** | API REST con FastAPI | Railway | Deploy desde Dockerfile, $PORT dinámico, healthcheck nativo, tier gratis |
| **CI** | Tests automáticos | GitHub Actions | Corre `pytest` en cada push a `main` (gate de calidad) |
| **CD** | Deploy a Railway | `railway up` | Deploy manual con un comando (auto-deploy activable conectando el repo en Railway) |
| **Documentación API** | Swagger UI | FastAPI (built-in) | Endpoint `/docs` autogenerado, ideal para demo |

Cada uno corre independiente. Si Railway cae, Supabase sigue. Si la API se escala horizontalmente, la BD no se duplica. **No es monolito.**

### Contenedores por capa (docker-compose)

El pipeline no corre en un solo contenedor: **cada etapa (capa) es su propio contenedor**, definidos en [`docker-compose.yml`](docker-compose.yml). Asi cada componente se puede **modificar y escalar de forma independiente**.

```
[etapa1-ingesta] -> [etapa2-limpieza] -> [etapa3-validacion] -> [etapa4-carga] -> Supabase
   contenedor          contenedor           contenedor            contenedor
   data/source         data/raw             data/clean            data/validated
        \__________________ volumen de datos compartido (zonas) __________________/
```

- Cada capa se **mejora/modifica sin tocar las demas** (codigo y despliegue por modulo).
- Se **replica solo la etapa saturada**, no todo el sistema: `docker compose up --scale limpieza=3 limpieza`.
- Se comunican por un **volumen compartido**; el orden lo garantiza `depends_on` (cada etapa arranca cuando la anterior termino OK). Solo `carga` toca la BD (recibe `DATABASE_URL`).

```bash
docker compose up --build     # corre las 4 etapas, cada una en su contenedor
```

> La API REST en Railway expone esas mismas etapas como endpoints (gateway/orquestador para la demo en vivo): el pipeline por contenedores y la API **comparten el mismo codigo e imagen**. Cada etapa es ademas un modulo ejecutable por si solo (`python src/ingesta.py`, etc.).

---

## Pipeline de 4 etapas (cada una un endpoint independiente)

```
CSV fuente (data/source/ en repo · o Supabase Storage si se configura)
        │
        ▼
[POST /pipeline/ingest]    → data/raw/    (copia + timestamp + log)
        │
        ▼
[POST /pipeline/clean]     → data/clean/  (TotalCharges fix, booleanos, features)
        │
        ▼
[POST /pipeline/validate]  → data/validated/  + data/rejected/
        │
        ▼
[POST /pipeline/load]      → Supabase Postgres (tabla clientes + auditoría)

[POST /pipeline/run]       → ejecuta las 4 en cadena con KPIs
```

---

## Stack técnico

| Componente | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.11 |
| Framework API | FastAPI + Uvicorn | 0.110 / 0.27 |
| Manipulación datos | pandas | 2.1 |
| Validación estructural | pandera | 0.20+ |
| ORM / DB driver | SQLAlchemy + psycopg2 | 2.0 / 2.9 |
| Cliente Supabase | supabase-py | 2.4 |
| Containerización | Docker | latest |
| BD gestionada | PostgreSQL (Supabase) | 17 |
| Host backend | Railway | - |
| CI/CD | GitHub Actions | v4 |
| Modelado IA (EV3) | scikit-learn | 1.9 |
| Visualización (EV3) | matplotlib · seaborn | 3.11 · 0.13 |
| Dashboard BI (EV3) | Streamlit · Plotly | 1.49 · 6 |
| Seguimiento proyecto | Trello | - |

---

## Estructura del repositorio

```
telco-churn-pipeline/
├── README.md                       Esta guia
├── Dockerfile                      Imagen para Railway (sirve FastAPI)
├── railway.toml                    Config de Railway (build + deploy + health)
├── Procfile                        Comando alternativo (Heroku-style)
├── requirements.txt                Dependencias Python
├── .env.example                    Plantilla de variables (Supabase + Railway)
├── .gitignore                      Excluye datos, logs, credenciales, venv
├── .github/workflows/ci.yml        Tests automaticos en push
├── data/
│   ├── source/                     ★ Dataset fuente versionado (telco_churn_source.csv)
│   ├── raw/                        CSV ingestado con timestamp (efimero)
│   ├── clean/                      Post-limpieza (efimero)
│   ├── validated/                  Post-validacion, van a BD (efimero)
│   └── rejected/                   Fallaron validacion, con motivo (efimero)
├── src/
│   ├── api.py                      ★ FastAPI - endpoints de cada etapa
│   ├── ingesta.py                  Etapa 1 (repo / Supabase Storage / ruta local)
│   ├── limpieza.py                 Etapa 2
│   ├── validacion.py               Etapa 3
│   ├── carga_bd.py                 Etapa 4 (Supabase Postgres con SSL, idempotente)
│   ├── run_pipeline.py             Orquestador CLI standalone
│   ├── modelo.py                   ★ EV3 - entrena/evalua modelo churn + persiste predicciones
│   ├── benchmark.py                ★ EV3 - analisis de rendimiento en la nube (psutil)
│   └── utils/
│       ├── logger.py               Logger centralizado
│       ├── schema.py               Schema pandera + reglas semanticas
│       └── supabase_client.py      Cliente Storage (opcional)
├── dashboard/                      ★ EV3 - dashboard BI (Streamlit + Plotly)
│   ├── app.py                      Panel conectado a Supabase (predicciones)
│   └── requirements.txt            Deps del dashboard (deployable aparte)
├── deck/
│   └── index.html                  ★ EV3 - deck de defensa (HTML 4:3 + Chart.js)
├── outputs/                        ★ EV3 - artefactos reproducibles
│   ├── modelo/                     Metricas, graficos, predicciones del modelo
│   ├── seguridad/                  Auditoria de seguridad + pip-audit
│   ├── rendimiento/                Benchmark (psutil)
│   ├── limitaciones_mejoras.md     Limitaciones + propuestas de mejora
│   └── guion_defensa.md            Guion de la defensa (15 min)
├── sql/
│   ├── 01_create_tables.sql        DDL Postgres (ejecutar en Supabase SQL Editor)
│   └── 02_roles_seguridad.sql      ★ EV3 - rol de solo lectura (privilegio minimo)
├── scripts/
│   ├── gen_diagramas.py            Renderiza los diagramas Mermaid a PNG
│   ├── setup_supabase.py           Aplica DDL (y sube CSV a Storage si aplica)
│   └── inyectar_errores.py         Genera dataset roto para demo en vivo
├── tests/
│   └── test_validaciones.py        Tests unitarios (corren en GitHub Actions)
└── docs/
    ├── Informe_Tecnico_Evaluacion2.pdf   Informe academico Eval 2 (entregable)
    ├── Informe_Tecnico_Evaluacion3.pdf   ★ EV3 - Informe academico Eval 3 (12 pags)
    ├── diagramas.md                      Fuente Mermaid de los diagramas
    ├── DEPLOY.md                         Guia paso-a-paso de deploy cloud
    ├── img/                              Diagramas + evidencias (capturas)
    └── slides/README.md                  Presentacion (desplegada en Vercel)
```

---

## Setup inicial - Guía paso a paso

### 1. Configurar Supabase (5 min)

1. Crear cuenta gratis en https://supabase.com → "New project"
2. Elegir nombre (ej `telco-churn-data`), generar password, elegir región más cercana
3. Cuando esté listo (~2 min), ir a **SQL Editor** → "New query"
4. Copiar y pegar el contenido de [`sql/01_create_tables.sql`](sql/01_create_tables.sql) → "Run"
5. Verificar en **Table Editor** que aparecen `clientes`, `carga_logs`, `clientes_rechazados`
6. Ir a **Storage** → "New bucket" → nombre `telco-data`, hacerlo público
7. Subir el CSV fuente al bucket como `telco_churn_source.csv`
8. Ir a **Settings → Database** → copiar el **Connection string** (formato URI, modo Transaction)
9. Ir a **Settings → API** → copiar `URL` y `anon public` key

### 2. Configurar Railway (5 min)

1. Ir a https://railway.app → "Login with GitHub"
2. "New Project" → "Deploy from GitHub repo" → seleccionar este repo
3. Railway detectará el Dockerfile y empezará a buildear
4. Ir a "Variables" del servicio y agregar:
   ```
   DATABASE_URL=<connection string de Supabase paso 1.8>
   SUPABASE_URL=<URL de Supabase paso 1.9>
   SUPABASE_KEY=<anon key de Supabase paso 1.9>
   SUPABASE_BUCKET=telco-data
   SOURCE_CSV_FILENAME=telco_churn_source.csv
   LOG_LEVEL=INFO
   CORS_ORIGINS=*
   ```
5. En "Settings" → "Networking" → "Generate Domain" para obtener URL pública
6. Esperar primer deploy (~2 min) y verificar con `curl <tu-url>/health`

### 3. Activar GitHub Actions (1 min)

El workflow `.github/workflows/ci.yml` ya está incluido. Solo asegurarse de que en GitHub Settings → Actions → "Allow all actions and reusable workflows" esté activo. Cada push correrá los tests automáticamente.

### 4. Probar la API en producción

```bash
# Health check
curl https://<tu-app>.up.railway.app/health

# Documentacion Swagger UI
# Abrir en navegador: https://<tu-app>.up.railway.app/docs

# Ejecutar pipeline completo
curl -X POST https://<tu-app>.up.railway.app/pipeline/run

# Ver KPIs
curl https://<tu-app>.up.railway.app/kpis/resumen | python -m json.tool

# Ver ultimos logs
curl https://<tu-app>.up.railway.app/logs/last?lineas=20
```

---

## Desarrollo local (opcional)

Si quieres iterar antes de hacer push:

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Copiar .env.example a .env y completar con tus credenciales Supabase
cp .env.example .env

# Levantar API
uvicorn src.api:app --reload --port 8000

# En otro terminal, probar
curl http://localhost:8000/health
curl -X POST http://localhost:8000/pipeline/run

# Tests
pytest tests/ -v
```

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/` | Información de la API |
| GET | `/health` | Health check + estado de BD |
| GET | `/docs` | Swagger UI auto-generado |
| POST | `/pipeline/ingest` | Solo etapa 1 |
| POST | `/pipeline/clean` | Solo etapa 2 |
| POST | `/pipeline/validate` | Solo etapa 3 |
| POST | `/pipeline/load` | Solo etapa 4 |
| POST | `/pipeline/run` | Ejecuta las 4 en orden |
| GET | `/kpis/last?limit=10` | Últimas N ejecuciones |
| GET | `/kpis/resumen` | KPIs agregados |
| GET | `/logs/last?lineas=50` | Últimas N líneas del log de hoy |
| GET | `/rechazados?limit=20` | Últimos N rechazados con motivo |

---

## Demo en vivo (guion)

1. **Mostrar el repo en GitHub** — código versionado, Actions corriendo verde
2. **Mostrar Railway** — deploy exitoso, logs en vivo
3. **Mostrar Supabase** — Table Editor con las 3 tablas vacías
4. **Abrir el Swagger** (`/docs`) — todos los endpoints visibles y testeables
5. **Disparar `/pipeline/run`** desde el Swagger UI
6. **Volver a Supabase** → Table Editor → mostrar las 7.043 filas en `clientes`
7. **Mostrar `carga_logs`** — auditoría de la ejecución
8. **Disparar `/pipeline/ingest` con el dataset roto** (`scripts/inyectar_errores.py`)
9. **Mostrar `clientes_rechazados`** — 8 errores detectados con motivo
10. **Mostrar `/kpis/resumen`** — métricas agregadas

---

## Seguridad y reproducibilidad

- **Variables sensibles** en Railway Variables (nunca en código).
- **Conexión a Supabase forzada con SSL** (`sslmode=require`).
- **CORS configurable** vía `CORS_ORIGINS`.
- **GitHub Actions** valida en cada push que el código compila y los tests pasan.
- **Dockerfile reproducible**: pin de versiones, no `latest`.
- **Logs estructurados** sin datos personales.

Ver detalle del plan de seguridad en el [informe técnico](docs/Informe_Tecnico_Evaluacion2.pdf). La **auditoría de seguridad de Evaluación 3** (4 frentes + Ley 21.719) está en [`outputs/seguridad/auditoria_seguridad.md`](outputs/seguridad/auditoria_seguridad.md).

---

## Evaluación 3: modelo de IA, BI y seguridad

La Evaluación 3 construye **sobre el mismo pipeline**: usa los 7.043 clientes ya curados en `clientes` para entrenar un modelo, lo expone en BI y audita la seguridad del sistema.

| Componente | Archivo | Qué hace |
|---|---|---|
| **Modelo de churn** | [`src/modelo.py`](src/modelo.py) | Clasificación binaria supervisada. Baseline (Reg. Logística, Árbol) + mejora (Random Forest, Reg. Logística balanceada). Lee `clientes` desde Supabase, entrena con split **70/30 estratificado** y persiste las predicciones en la tabla `predicciones`. |
| **Dashboard BI** | [`dashboard/app.py`](dashboard/app.py) | Panel **Streamlit + Plotly** conectado a Supabase: KPIs, matriz de confusión, tabla filtrable de errores y embudo de volumen por etapa. |
| **Seguridad + Ley 21.719** | [`outputs/seguridad/`](outputs/seguridad/) · [`sql/02_roles_seguridad.sql`](sql/02_roles_seguridad.sql) | Auditoría en 4 frentes (credenciales, accesos/RLS, dependencias, logs) + rol de solo lectura (privilegio mínimo) + mapeo *compliance by design* a la nueva ley de datos personales. |
| **Rendimiento nube** | [`src/benchmark.py`](src/benchmark.py) | Mide con `psutil`/`time` el costo de cada operación (lectura local vs nube vs entrenamiento). |

**Modelo elegido:** Regresión Logística balanceada — **recall 79,7%**, F1 0,62, **Gini 0,69**, ROC-AUC 0,85 (sobre el conjunto de prueba). Se prioriza el recall porque el falso negativo —un cliente que se va sin detectar— es el error más caro en retención.

**Cómo ejecutarlo** (requiere `.env` con `DATABASE_URL` y las deps de `requirements.txt`):
```bash
# Entrenar el modelo desde Supabase y persistir las predicciones
python src/modelo.py --fuente supabase --persistir

# Medir el rendimiento
python src/benchmark.py

# Levantar el dashboard BI (http://localhost:8501)
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Informe completo (12 págs) en [`docs/Informe_Tecnico_Evaluacion3.pdf`](docs/Informe_Tecnico_Evaluacion3.pdf) · deck en [Vercel](https://deck-benjaminheresmanns-projects.vercel.app).

---

## Referencias

- Dataset: IBM Sample Data Sets - Telco Customer Churn (Kaggle)
- Material del curso (Eval 2): PDFs 2.1 a 2.4 - Pipeline de Datos
- Material del curso (Eval 3): 3.1 a 3.4 - Modelo IA supervisado, rendimiento, seguridad, visualización
- scikit-learn docs: https://scikit-learn.org · Streamlit: https://streamlit.io
- Supabase docs: https://supabase.com/docs
- Railway docs: https://docs.railway.app
- FastAPI docs: https://fastapi.tiangolo.com
