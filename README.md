# Pipeline de Datos - Telco Customer Churn

Pipeline DataOps de 4 etapas para preparar el dataset Telco Customer Churn (IBM Sample Data Set, 7.044 clientes) y dejarlo cargado en PostgreSQL listo para entrenar un modelo de prediccion de abandono.

**Asignatura:** ITY1101 Gestion de Datos para IA - Duoc UC
**Evaluacion:** Parcial N°2
**Integrantes:** Benjamin Heresmann, Diego Hernandez

---

## Arquitectura

Pipeline modular con 4 etapas secuenciales, orquestadas por `src/run_pipeline.py`:

```
CSV fuente
    |
    v
[1. Ingesta]        --> data/raw/         (copia con sello temporal + log)
    |
    v
[2. Limpieza]       --> data/clean/       (TotalCharges -> float, booleanos, features)
    |
    v
[3. Validacion]     --> data/validated/   (pandera estructural + reglas semanticas)
                    --> data/rejected/    (registros con motivo de rechazo)
    |
    v
[4. Carga BD]       --> PostgreSQL        (tabla clientes + auditoria carga_logs)
```

Cada etapa es un script Python independiente que tambien puede correrse por separado, util para debugging y demos.

---

## Stack tecnico

| Componente            | Tecnologia              | Justificacion |
|-----------------------|-------------------------|---------------|
| Lenguaje              | Python 3.11             | Enseñado en clases, ecosistema maduro para datos |
| Manipulacion datos    | pandas 2.1              | Estandar de facto para CSV/tabular |
| Validacion estructural| pandera 0.18            | Declarativo, integra con pandas, mensajes claros |
| Validacion semantica  | Funciones Python puras  | Reglas de negocio simples e inspectables |
| Base de datos         | PostgreSQL 15           | Relacional robusta, restricciones declarativas |
| ORM / conexion        | SQLAlchemy + psycopg2   | Estandar para Postgres en Python |
| Contenedorizacion     | Docker + docker-compose | Entorno reproducible, requisito de la rubrica |
| Control de versiones  | Git + GitHub            | Trazabilidad y colaboracion |
| Seguimiento proyecto  | Trello (kanban)         | Simple, suficiente para equipo de 2 |

---

## Estructura del repositorio

```
telco-churn-pipeline/
├── README.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── raw/            # CSV ingestado con timestamp
│   ├── clean/          # Despues de limpieza/transformacion
│   ├── validated/      # Aprobado por validaciones
│   └── rejected/       # Falló alguna validacion (con motivo)
├── src/
│   ├── ingesta.py      # Etapa 1
│   ├── limpieza.py     # Etapa 2
│   ├── validacion.py   # Etapa 3
│   ├── carga_bd.py     # Etapa 4
│   ├── run_pipeline.py # Orquestador
│   └── utils/
│       ├── logger.py   # Logging unificado
│       └── schema.py   # Esquema pandera + reglas semanticas
├── sql/
│   └── 01_create_tables.sql  # DDL Postgres
├── logs/               # Archivos .log por dia de ejecucion
├── tests/
│   └── test_validaciones.py
└── docs/
    ├── informe_tecnico.pdf
    ├── presentacion.pdf
    ├── arquitectura.png
    └── flujo_datos.png
```

---

## Requisitos

- Docker Desktop instalado (incluye docker-compose v2)
- Git
- (Opcional para desarrollo local sin Docker) Python 3.11

---

## Como levantar el proyecto

### Opcion A - Todo con Docker (recomendado para demo)

1. Clonar el repositorio:
   ```bash
   git clone <url-del-repo>
   cd telco-churn-pipeline
   ```

2. Copiar `.env.example` a `.env` y ajustar credenciales:
   ```bash
   cp .env.example .env
   ```

3. Levantar PostgreSQL (la primera vez creara las tablas con el DDL):
   ```bash
   docker compose up -d postgres
   ```

4. Esperar a que el healthcheck pase y ejecutar el pipeline:
   ```bash
   docker compose run --rm pipeline
   ```

5. Inspeccionar resultados:
   ```bash
   docker compose exec postgres psql -U pipeline_user -d telco_churn \
     -c "SELECT churn, COUNT(*) FROM clientes GROUP BY churn;"

   docker compose exec postgres psql -U pipeline_user -d telco_churn \
     -c "SELECT * FROM carga_logs ORDER BY fecha_ejecucion DESC LIMIT 5;"
   ```

### Opcion B - Pipeline local, Postgres en Docker

1. Levantar solo Postgres:
   ```bash
   docker compose up -d postgres
   ```

2. Instalar dependencias Python:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```

3. Ejecutar el pipeline completo:
   ```bash
   python src/run_pipeline.py
   ```

4. O ejecutar etapas individuales:
   ```bash
   python src/ingesta.py
   python src/limpieza.py
   python src/validacion.py
   python src/carga_bd.py
   ```

---

## Ejecutar tests

```bash
pytest tests/ -v
```

Los tests cubren las reglas de validacion semantica (cruzadas entre `InternetService`, `PhoneService` y sus servicios derivados).

---

## Etapas del pipeline en detalle

### 1. Ingesta (`src/ingesta.py`)
- Lee el CSV fuente desde la ruta definida en `SOURCE_CSV_PATH`.
- Copia el archivo a `data/raw/telco_churn_raw_YYYYMMDD_HHMMSS.csv`.
- Registra en log: archivo origen, filas leidas, columnas, timestamp.

### 2. Limpieza y transformacion (`src/limpieza.py`)
- Detecta y convierte `TotalCharges` (string con celdas vacias) a float con NaN.
- Normaliza columnas Yes/No a booleano: `Partner`, `Dependents`, `PhoneService`, `PaperlessBilling`, `Churn`.
- Elimina duplicados por `customerID`.
- Crea feature derivada `tenure_group`: 0-12, 13-24, 25-48, 49-72, 73+ meses.
- Guarda en `data/clean/`.

### 3. Validacion estructural y semantica (`src/validacion.py`)
- **Estructural (pandera):** tipos por columna, rangos numericos, valores permitidos en categoricas, formato de `customerID` (`####-AAAAA`).
- **Semantica (reglas if/else):**
  - Si `InternetService = No`, todos los servicios derivados deben ser `No internet service`.
  - Si `InternetService != No`, ningun servicio puede ser `No internet service`.
  - Si `PhoneService = False`, `MultipleLines` debe ser `No phone service` (y vice-versa).
  - Coherencia `TotalCharges` con `MonthlyCharges * tenure`.
- Filas validas -> `data/validated/`. Filas invalidas -> `data/rejected/` con motivo.

### 4. Carga a PostgreSQL (`src/carga_bd.py`)
- Conecta a Postgres con SQLAlchemy + psycopg2.
- Inserta validados en `clientes` dentro de una transaccion (rollback si falla).
- Audita rechazados en `clientes_rechazados` con payload JSONB y motivo.
- Registra ejecucion en `carga_logs`: archivo, conteos, duracion, estado.

---

## KPIs de monitoreo

Cada ejecucion del orquestador imprime y persiste:

| KPI                          | Donde se mide |
|------------------------------|--------------------------|
| Latencia por etapa (seg)     | Logs + tabla carga_logs  |
| Registros leidos             | Logs + tabla carga_logs  |
| Registros insertados         | Logs + tabla carga_logs  |
| Registros rechazados         | Logs + tabla carga_logs  |
| % de validez                 | Calculado en validacion  |
| Completitud por columna      | Calculado en limpieza    |
| Estado de ejecucion          | OK / ERROR / PARCIAL     |

---

## Plan de seguridad DataOps

1. **Ley 19.628 (Chile)** - el dataset contiene datos personales (ID cliente, edad, situacion familiar, datos financieros). Tratamiento limitado al proposito declarado.
2. **Cifrado en transito** - conexion a Postgres via TLS en produccion.
3. **Cifrado en reposo** - volumenes Docker con cifrado a nivel sistema operativo en produccion.
4. **Control de acceso** - rol `telco_analista` con `SELECT` sobre `clientes` y sin `INSERT/UPDATE/DELETE` (ejemplo comentado en `sql/01_create_tables.sql`).
5. **Credenciales** - variables de entorno (`.env`), nunca en codigo o git.
6. **Logs sin PII** - los logs registran conteos y tipos de error, no valores de columnas sensibles.
7. **Auditoria** - tabla `carga_logs` mantiene historial completo de ejecuciones.
8. **Enmascaramiento** - `customerID` puede hashearse antes de exponer a analitica si se requiere mayor proteccion.

---

## Flujo end-to-end con datos del caso

Salida esperada al correr `python src/run_pipeline.py`:

```
INFO | orquestador | INICIO PIPELINE TELCO CHURN
INFO | ingesta     | Iniciando ingesta desde .../02_Base_...csv
INFO | ingesta     | Ingesta completada | filas=7043 | columnas=21
INFO | limpieza    | TotalCharges: 11 celdas vacias convertidas a NaN
INFO | limpieza    | Limpieza completada | filas=7043 -> 7043 | nulos=11 | duplicados=0
INFO | validacion  | Validacion estructural: 7032 ok, 11 rechazados
INFO | validacion  | Validacion semantica:  7032 ok, 0 rechazados
INFO | carga_bd    | Insertados 7032 registros en clientes
INFO | orquestador | FIN PIPELINE | duracion total = ~3 seg
```

---

## Continuidad con Evaluacion 3

El dataset cargado en `clientes` queda listo para entrenar un modelo de clasificacion binaria sobre el target `churn`. Variables candidatas: `tenure`, `Contract`, `MonthlyCharges`, `InternetService`, `PaymentMethod`.

---

## Referencias

- Dataset: IBM Sample Data Sets - Telco Customer Churn (Kaggle)
- Material de clases: PDF 2.1 a 2.4 del modulo Pipeline de Datos
- Rubrica: Evaluacion Parcial N°2, ITY1101 Gestion de Datos para IA
