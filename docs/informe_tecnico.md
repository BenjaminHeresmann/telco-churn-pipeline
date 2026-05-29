# Informe Técnico — Evaluación Parcial N°2
## Pipeline DataOps para Predicción de Churn en Telecomunicaciones

**Asignatura:** ITY1101 Gestión de Datos para IA
**Institución:** Duoc UC
**Evaluación:** Parcial N°2 (35%)
**Equipo:** Benjamín Heresmann · Diego Hernández
**Fecha de entrega:** 2 de junio de 2026

---

## Índice

1. Resumen ejecutivo
2. Justificación de la metodología PMBOK aplicada
3. Planificación del proyecto
4. Explicación técnica del pipeline
   4.1 Etapa 1 — Ingesta
   4.2 Etapa 2 — Limpieza y transformación
   4.3 Etapa 3 — Validación estructural y semántica
   4.4 Etapa 4 — Carga a base de datos
5. Plan de seguridad para entorno DataOps
6. Documentación del código y evidencias
7. Estrategia de KPIs de monitoreo
8. Conclusiones y próximos pasos

---

## 1. Resumen ejecutivo

Este informe documenta el diseño, planificación e implementación de un pipeline de datos automatizado bajo principios DataOps para una compañía de telecomunicaciones que enfrenta un alto índice de abandono de clientes (churn). El proyecto utiliza el dataset público "Telco Customer Churn" (7.043 clientes, 21 variables) como base para construir un flujo de cuatro etapas (ingesta, limpieza/transformación, validación estructural y semántica, y carga a base de datos relacional) que deja la información lista para alimentar un modelo predictivo de IA.

El valor para la organización es doble. Por una parte, el pipeline reduce el costo operativo de preparación de datos al automatizar las etapas que tradicionalmente se hacen manualmente con planillas, eliminando errores humanos y aumentando la frecuencia con que el negocio puede recalibrar su estrategia de retención. Por otra parte, sienta las bases para la Evaluación 3, en la que se entrenará un modelo de clasificación binaria sobre la variable Churn, permitiendo focalizar campañas de retención sobre los clientes con mayor probabilidad de abandono y, en consecuencia, proteger los ingresos recurrentes de la compañía.

La solución se implementa con una **arquitectura cloud-native desacoplada**: el procesamiento corre como API REST en FastAPI desplegada en **Railway** (capa de cómputo), la persistencia usa PostgreSQL gestionado en **Supabase** (capa de datos), el dataset fuente viaja versionado en el repositorio (y opcionalmente puede leerse desde Supabase Storage), y el código se versiona en GitHub con **CI automatizado** (tests en cada push vía GitHub Actions) y **CD por comando** (`railway up`). No es un monolito: cada componente escala, despliega y se mantiene de forma independiente, comunicándose mediante interfaces estándar (HTTPS REST y SQL sobre TLS).

El equipo está autorizado por el docente a operar con **dos integrantes** (Benjamín Heresmann y Diego Hernández), con división equitativa de responsabilidades técnicas pero defensa individual de la solución completa.

---

## 2. Justificación de la metodología PMBOK aplicada

El proyecto adopta un **enfoque híbrido del PMBOK 7ª edición** (predictivo + adaptativo), por las siguientes razones.

El componente **predictivo** se aplica sobre las actividades cuyos requisitos son fijos y dependencias técnicas son claras: el modelado de la base de datos relacional, la definición del esquema de validación, la construcción del Dockerfile y la integración con el repositorio remoto. Para estas tareas se planifica con cronograma, hitos y entregables específicos en una carta Gantt; el cambio mid-proyecto sería costoso y desordenaría el equipo.

El componente **adaptativo** se aplica sobre las actividades exploratorias o que dependen de hallazgos iterativos: el ajuste fino de las reglas de validación semántica (que sólo se descubren al inspeccionar los datos reales), la afinación de los KPIs de monitoreo (que se redefinen al ver qué métricas son realmente accionables) y la preparación de la demo en vivo (que se itera con ensayos). Para estas tareas se trabaja en ciclos cortos con revisión cruzada entre los dos integrantes.

Esta combinación es coherente con un proyecto académico de 7 días con un equipo de 2 personas. Una metodología puramente predictiva sería rígida frente a los hallazgos que aparezcan al procesar el dataset por primera vez; una puramente ágil sería caótica para coordinar las dependencias técnicas entre el modelo de BD y los scripts del pipeline.

Para el seguimiento operativo se usa un tablero **Trello** con tres columnas (Por hacer, En progreso, Terminado), una columna lateral con criterios de aceptación por entregable, y reuniones diarias breves entre los integrantes. Trello fue elegido por sobre Jira o Azure DevOps por su simplicidad y porque el equipo es pequeño; no se justifica la complejidad de herramientas empresariales para esta escala.

---

## 3. Planificación del proyecto

### 3.1 Estructura de Desglose del Trabajo (WBS)

| Fase | Actividad principal | Entregable | Responsable | Días |
|---|---|---|---|---|
| **1. Setup** | Definición de arquitectura, stack y repositorio | Repo inicial + estructura | Benjamín | 1 |
| **1. Setup** | Configuración Docker + PostgreSQL + DDL | docker-compose.yml + DDL | Diego | 1 |
| **2. Pipeline** | Implementar etapa 1 (Ingesta) | `src/ingesta.py` + logs | Benjamín | 1 |
| **2. Pipeline** | Implementar etapa 2 (Limpieza) | `src/limpieza.py` | Diego | 1 |
| **2. Pipeline** | Implementar etapa 3 (Validación) | `src/validacion.py` + schema | Benjamín | 1 |
| **2. Pipeline** | Implementar etapa 4 (Carga BD) | `src/carga_bd.py` | Diego | 1 |
| **2. Pipeline** | Orquestador + KPIs | `src/run_pipeline.py` | Ambos | 1 |
| **3. Calidad** | Tests, plan seguridad, refinamiento | tests + README final | Ambos | 1 |
| **4. Doc** | Informe técnico + diagramas | PDF informe | Benjamín | 2 |
| **4. Doc** | Slides + demo + ensayo | PPT + demo guion | Diego | 2 |

### 3.2 Hitos clave

- **H1 — Stack y entorno funcional**: Postgres levanta, Docker construye, primera prueba de ingesta exitosa.
- **H2 — Pipeline end-to-end**: las 4 etapas se ejecutan secuencialmente y la BD queda poblada con datos válidos.
- **H3 — Documentación completa**: informe revisado, diagramas exportados, slides listos y demo ensayada.

### 3.3 Carta Gantt

Ver `docs/diagramas.md` — diagrama 5 (renderizado con Mermaid).

### 3.4 Herramienta de seguimiento

**Trello** con un tablero por cada hito. Cada tarjeta incluye: descripción, responsable, definición de "Terminado", y enlace al commit o entregable. La elección sobre Jira/Azure DevOps responde al tamaño del equipo (2 personas) y la duración del proyecto (7 días), donde la sobrecarga de herramientas empresariales no se justifica.

---

## 4. Arquitectura cloud desacoplada

A pedido del docente, la solución NO es un monolito y debe quedar desplegada en la nube. Se diseña una arquitectura de tres servicios independientes que se comunican mediante interfaces estándar.

### 4.0.1 Servicios

| Servicio | Tecnología | Rol | Justificación |
|---|---|---|---|
| **Capa de datos** | Supabase (PostgreSQL 17) | Persiste los datos curados, auditoría y rechazados | PostgreSQL gestionado con SSL out-of-the-box, UI web para inspección, plan gratis suficiente para el alcance académico. Incluye Storage S3-compatible (usado opcionalmente para el CSV fuente) |
| **Capa de cómputo** | Railway (Docker + FastAPI) | Ejecuta el pipeline expuesto como API REST | Deploy directo desde Dockerfile, puerto dinámico, healthchecks nativos, escalado horizontal, plan gratis |
| **CI** | GitHub Actions | Valida cada cambio | Tests `pytest` automáticos en cada push; integración nativa con GitHub |
| **CD** | `railway up` | Promueve a producción | Deploy manual por comando (gate humano); auto-deploy activable conectando el repo en Railway |

### 4.0.2 Por qué no monolito

Una arquitectura monolítica habría empaquetado todo (BD + pipeline + UI) en un único contenedor. Eso:

- Acopla el ciclo de vida de los datos al ciclo de vida del código (no puedes hacer rolling deploy del pipeline sin downtime de BD).
- Impide escalar de forma diferenciada (la BD necesita storage; el pipeline necesita CPU para procesamiento).
- Dificulta la sustitución de componentes (si mañana cambian Supabase por AWS RDS, sólo se actualiza la connection string).
- Concentra el blast radius de un fallo: si la BD se corrompe, el contenedor entero queda inutilizable.

Con desacoplamiento, cada servicio puede:

- Actualizarse, escalarse y reiniciarse independientemente.
- Tener métricas y alertas separadas.
- Reemplazarse por una alternativa equivalente sin tocar a los demás (siempre que respeten el contrato API/SQL).

### 4.0.3 Endpoints REST expuestos

La capa de cómputo es una API FastAPI con los siguientes endpoints (autodocumentados en `/docs` vía Swagger UI):

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/` | Información de la API |
| GET | `/health` | Estado del servicio y de la BD |
| GET | `/docs` | Swagger UI interactivo (autogenerado) |
| POST | `/pipeline/ingest` | Ejecuta solo etapa 1 (ingesta desde Supabase Storage) |
| POST | `/pipeline/clean` | Ejecuta solo etapa 2 (limpieza) |
| POST | `/pipeline/validate` | Ejecuta solo etapa 3 (validación) |
| POST | `/pipeline/load` | Ejecuta solo etapa 4 (carga a Supabase BD) |
| POST | `/pipeline/run` | Ejecuta las 4 etapas en orden con KPIs |
| GET | `/kpis/last?limit=N` | Últimas N ejecuciones desde `carga_logs` |
| GET | `/kpis/resumen` | KPIs agregados (totales, promedios, tasas) |
| GET | `/logs/last?lineas=N` | Últimas N líneas del log de hoy |
| GET | `/rechazados?limit=N` | Últimos N registros rechazados con motivo |

Esta granularidad permite que sistemas externos (un job de Airflow, un script en cron, un dashboard web) consuman partes específicas del pipeline sin tener que importarlo como librería.

### 4.0.4 Flujo de integración y despliegue

```
Desarrollador hace git push a main
         │
         ▼
[CI] GitHub Actions corre pytest (tests/)  → badge verde si OK
         │
         ▼
Desarrollador ejecuta: railway up --service telco-api   (CD por comando)
         │
         ▼
Railway rebuilda la imagen Docker desde Dockerfile (cache de capas)
         │
         ▼
Railway hace rolling deploy (sin downtime)
         │
         ▼
Healthcheck en /health verifica que está operativo
         │
         ▼
Tráfico se enruta al nuevo deploy
```

El paso de CI (tests) es automático en cada push; el paso de CD (deploy) es un
comando explícito, lo que da un gate humano antes de promover a producción.
Activar auto-deploy es trivial (conectar el repo en Railway) si se desea CD
totalmente automático. Tiempo total push → producción: ~3-5 minutos.

### 4.0.5 Variables de entorno (Railway)

Toda la configuración sensible se inyecta como variables de entorno en Railway (nunca en código):

- `DATABASE_URL` — connection string completo de Supabase (con SSL)
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_BUCKET` — para descargar el CSV desde Storage
- `SOURCE_CSV_FILENAME` — nombre del archivo en el bucket
- `LOG_LEVEL` — granularidad de logging
- `CORS_ORIGINS` — orígenes permitidos para CORS (frontend opcional)
- `PORT` — inyectado por Railway automáticamente

---

## 4. Explicación técnica del pipeline

### 4.1 Etapa 1 — Ingesta automatizada

**Objetivo:** capturar el CSV fuente y depositarlo en una zona controlada (`data/raw/`) con trazabilidad temporal, sin transformar el contenido.

**Implementación:** script `src/ingesta.py` que deposita el CSV en `data/raw/` con un sufijo de timestamp (`telco_churn_raw_YYYYMMDD_HHMMSS.csv`) y registra en el log el número de filas, columnas y la ruta destino. La estrategia de fuentes tiene cuatro niveles de prioridad: (1) parámetro explícito si se pasa, (2) **Supabase Storage** si están seteadas `SUPABASE_URL` y `SUPABASE_KEY`, (3) ruta local específica vía `SOURCE_CSV_PATH`, y (4) **fallback por defecto: el dataset versionado en el repo** (`data/source/telco_churn_source.csv`). En el despliegue MVP se usa el nivel (4): el dataset viaja dentro de la imagen Docker, por lo que la ingesta no depende de ningún servicio externo. El mismo código corre en cloud y en local sin modificaciones, y puede conmutarse a Supabase Storage solo agregando dos variables de entorno.

**Decisiones técnicas y alternativas evaluadas:**

- *Tipo de ingesta elegido:* **por lotes (batch)**. El dataset es un CSV estático, por lo que streaming/Kafka serían sobreingeniería injustificada.
- *Por qué el dataset versionado en el repo (MVP) y no Supabase Storage:* para el alcance del caso (dataset estático único), versionar el CSV en el repo lo hace reproducible, lo incluye en la imagen Docker y elimina un punto de falla y de configuración en la demo. Supabase Storage (S3-compatible, incluido en el plan gratis) queda implementado y disponible como fuente alternativa para cuando el dato sea dinámico o de gran tamaño.
- *Alternativa descartada — ingesta vía API REST:* el caso no expone API de la compañía, y un wrapper artificial sólo agregaría latencia. Si en el futuro la compañía expone un endpoint para extraer churn desde su CRM, basta con sustituir esta etapa.
- *Trazabilidad:* el sufijo de timestamp permite mantener histórico de cargas y reproducibilidad. El logger escribe simultáneamente a consola (para demo) y a archivo (para auditoría).

**Manejo de anomalías:**
- Archivo fuente no existe → `FileNotFoundError` explícito y `exit code 1`.
- Variable de entorno faltante → `ValueError` con mensaje claro.
- Lectura corrupta → `pandas` arroja excepción que es capturada y registrada.

### 4.2 Etapa 2 — Limpieza y transformación

**Objetivo:** convertir los datos crudos en un dataset normalizado y enriquecido, sin todavía aplicar reglas de negocio.

**Implementación:** script `src/limpieza.py` que aplica cinco operaciones:

1. **Corrección de tipo en `TotalCharges`**: el dataset tiene un bug conocido donde 11 registros traen este campo como string vacío (" "). Se convierte a numérico con `pd.to_numeric(errors="coerce")` y los inválidos quedan como NaN para que la siguiente etapa decida.
2. **Normalización de columnas booleanas**: `Partner`, `Dependents`, `PhoneService`, `PaperlessBilling`, `Churn` pasan de "Yes"/"No" a `True`/`False`. Las columnas categóricas ternarias (con "No internet service" o "No phone service") se mantienen como string porque ese tercer valor tiene significado semántico que no se debe perder.
3. **Limpieza de espacios** en nombres de columnas con `df.columns.str.strip()`.
4. **Detección y remoción de duplicados** por `customerID`, con log de cuántos se removieron.
5. **Creación de feature derivada `tenure_group`**: agrupa los meses de antigüedad en cinco bins (0-12, 13-24, 25-48, 49-72, 73+), facilitando análisis y futuro encoding del modelo.

**Decisiones técnicas y alternativas evaluadas:**

- *Por qué no eliminar los 11 nulos en `TotalCharges` aquí:* la decisión de qué hacer con un nulo es responsabilidad de la validación (etapa 3), no de la limpieza. Esto mantiene las responsabilidades separadas y permite que las reglas de negocio decidan caso a caso.
- *Alternativa descartada — `OrdinalEncoder` para tenure_group:* esa transformación pertenece al pipeline de ML (Evaluación 3), no a este pipeline de datos.
- *Idempotencia:* la limpieza siempre produce el mismo resultado para el mismo input, sin depender de estado externo.

**Manejo de anomalías:**
- Archivo crudo no existe → `FileNotFoundError`.
- Columna esperada faltante → `KeyError` registrado en log.
- Caracteres extraños en `customerID` → preservados, la siguiente etapa los rechazará si no cumplen el patrón.

### 4.3 Etapa 3 — Validación estructural y semántica

**Objetivo:** garantizar que sólo lleguen a la base de datos registros que cumplen tanto los requisitos técnicos (tipos, rangos, formatos) como las reglas de negocio (coherencia entre campos).

**Implementación:** script `src/validacion.py` que aplica dos pasadas:

**A) Validación estructural** con `pandera`:
- Tipos por columna (`int`, `str`, `bool`, `float`).
- Rangos numéricos: `tenure` entre 0 y 100; `MonthlyCharges` entre 0 y 1000; `TotalCharges` entre 0 y 100.000.
- Valores permitidos en categóricas: `gender ∈ {Male, Female}`, `Contract ∈ {Month-to-month, One year, Two year}`, etc.
- Formato de `customerID` con expresión regular `^\d{4}-[A-Z]{5}$`.
- Unicidad de `customerID`.

**B) Validación semántica** con reglas de negocio en Python puro:
- **Coherencia de servicios de internet**: si `InternetService = "No"`, los seis servicios derivados (`OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`) deben ser exactamente `"No internet service"`. Si no, se rechaza.
- **Inversa de la anterior**: si `InternetService ≠ "No"`, ninguno de esos servicios puede ser `"No internet service"`.
- **Coherencia de telefonía**: si `PhoneService = False`, `MultipleLines` debe ser `"No phone service"`; y vice-versa.
- **Coherencia financiera**: si `tenure > 0` y `MonthlyCharges > 0`, entonces `TotalCharges` no puede ser menor al 50% de `MonthlyCharges × 1` (margen para descuentos iniciales).

**Decisiones técnicas y alternativas evaluadas:**

- *Por qué pandera y no Great Expectations:* GE es más potente pero introduce overhead de configuración (suites, expectations, datadocs) que no se justifica para un proyecto académico. Pandera permite definir el schema en código Python puro, integra nativamente con pandas y produce mensajes de error inspeccionables.
- *Por qué separar válidos e inválidos en lugar de bloquear toda la carga:* permite procesar el "lote bueno" y dejar trazabilidad de los rechazados para auditoría y mejora continua. Esto es coherente con el principio DataOps de "fail soft, log loud".
- *Por qué reglas semánticas en Python puro y no en SQL:* validar antes de cargar evita transacciones rotas y permite mensajes de error mucho más claros para el operador.

**Manejo de anomalías:**
- Cada rechazo se guarda en `data/rejected/` con dos columnas extra: `motivo_rechazo` (texto descriptivo) y `tipo_validacion` ("estructural" o "semantica").
- Los registros inválidos también se insertan en la tabla `clientes_rechazados` (etapa 4), con el payload original en JSONB para análisis posterior.

### 4.4 Etapa 4 — Carga a base de datos

**Objetivo:** persistir los registros validados en **Supabase PostgreSQL** garantizando integridad de los datos, dentro de transacciones que permitan rollback ante fallos, con conexión cifrada vía SSL.

**Nota sobre el modelo de datos y la "integridad referencial":** el dataset es analítico de una sola entidad (cada fila es un cliente con todos sus atributos planos), por lo que el modelo es de **tabla única desnormalizada** (`clientes`), sin claves foráneas entre entidades. No habría integridad *referencial* que imponer porque no hay relaciones entre tablas de negocio. La integridad de datos se garantiza con otros mecanismos a nivel de motor: **clave primaria** (`customer_id` único e irrepetible), **restricciones CHECK** (rangos de `tenure`, valores permitidos de `gender`, `contract`, `internet_service`, `monthly_charges >= 0`, etc.), **NOT NULL** en columnas obligatorias y **transacciones atómicas**. Las tablas `carga_logs` y `clientes_rechazados` son de auditoría independiente (relación lógica por fecha/timestamp, no por FK), lo que simplifica las recargas full-refresh. Si el caso evolucionara a un modelo multi-entidad (ej. separar `cliente`, `contrato`, `servicio`), ahí sí se introducirían claves foráneas y su integridad referencial.

**Implementación:** script `src/carga_bd.py` que:

1. Construye la conexión con SQLAlchemy + psycopg2 a partir del `DATABASE_URL` que entrega Supabase, o ensambla la URL desde variables individuales forzando `sslmode=require`. El engine se cachea (singleton) para reutilizar el pool de conexiones en todas las requests, evitando agotar el límite del pooler de Supabase.
2. Renombra las columnas del DataFrame al `snake_case` esperado por la tabla `clientes`.
3. **Carga full-refresh idempotente:** dentro de una transacción, hace `TRUNCATE` de `clientes` y `clientes_rechazados` y luego inserta en bloques de 500 (`chunksize=500`) con `to_sql(method="multi")`. Reejecutar el pipeline produce siempre el mismo estado final (reproducibilidad DataOps), sin errores de clave duplicada. El histórico de auditoría (`carga_logs`) nunca se trunca.
4. Toda la operación TRUNCATE+INSERT ocurre dentro de un `engine.begin()` que garantiza COMMIT/ROLLBACK atómico: si el insert falla, la tabla queda intacta.
5. Si la etapa 3 generó rechazados (emparejados por timestamp con el archivo validado de la misma corrida), los inserta en `clientes_rechazados` con el payload serializado a JSONB y el motivo del rechazo.
6. Registra cada ejecución en `carga_logs` con archivo origen, conteos, duración y estado (OK/ERROR/PARCIAL).

**Decisiones técnicas y alternativas evaluadas:**

- *Por qué Supabase y no AWS RDS, Azure Database o auto-hosted:* Supabase ofrece PostgreSQL gestionado con interfaz web amigable (Table Editor, SQL Editor), tiene plan gratuito generoso para proyectos académicos (500MB de BD + 1GB de Storage), incluye Storage S3-compatible en el mismo servicio (evita gestionar AWS S3 aparte) y soporta SSL nativo sin configuración adicional. La connection string viene lista para producción.
- *Por qué pooler en puerto 6543 y no conexión directa en 5432:* el pooler de Supabase (PgBouncer en modo Transaction) maneja conexiones de servicios serverless de manera más eficiente, evitando agotar las ~60 conexiones simultáneas que permite el tier gratis. Railway al ser un servicio cloud puede crear y destruir conexiones rápidamente.
- *Por qué SQLAlchemy y no psycopg2 directo:* SQLAlchemy ofrece abstracción sobre dialectos (facilita migrar a otro motor si se requiere) y un manejo transaccional más limpio. Para cargas de millones de filas se evaluaría usar `COPY` directo, pero para 7.000 filas `to_sql(method="multi")` es suficientemente rápido (~1 segundo).
- *Por qué un esquema único `clientes` y no normalizar:* el dataset es analítico (cada fila es un cliente con sus atributos planos), no transaccional. Una normalización 3FN sería sobreingeniería que dificultaría el join para el modelo de IA en Evaluación 3.
- *Auditoría:* la tabla `carga_logs` es la fuente única de verdad sobre cuándo, qué y con qué éxito se ha ejecutado el pipeline. Soporta consultas como "muéstrame las ejecuciones que rechazaron más del 5% de registros en los últimos 7 días".

**Manejo de anomalías:**
- Conexión BD caída → captura `SQLAlchemyError`, registra estado "ERROR" en `carga_logs`.
- Violación de constraint (PK duplicada, CHECK fallido) → rollback automático de la transacción.
- Datos rechazados que fallan al auditar → no detiene la carga principal, sólo loguea warning.

---

## 5. Plan de seguridad para entorno DataOps

El pipeline maneja datos personales bajo el alcance de la **Ley 19.628 de Protección de la Vida Privada** (Chile), que regula el tratamiento de datos personales, y debe alinearse con principios equivalentes a los del GDPR europeo cuando se trabaje con clientes internacionales.

### 5.1 Marco legal aplicable

| Norma | Aplicación al proyecto |
|---|---|
| **Ley 19.628 (Chile)** | Datos personales: ID cliente, edad senior, dependientes, datos financieros. Obliga a recolectar con propósito específico, no usar para otros fines, y permitir derecho de acceso/rectificación. |
| **Ley 21.096 (Reforma constitucional Chile)** | Protección de datos personales como derecho fundamental. |
| **Ley 21.459 (Delitos informáticos)** | Tipifica acceso ilícito, interceptación y falsificación; aplica a la infraestructura del pipeline. |
| **ISO/IEC 27001** (referencia) | Sistema de gestión de seguridad de la información; el pipeline implementa controles compatibles. |

### 5.2 Técnicas de seguridad implementadas

**Cifrado en reposo:**
- Volumen Docker `postgres_data` montado sobre disco cifrado a nivel sistema operativo en producción (BitLocker en Windows, LUKS en Linux).
- Opción de cifrado a nivel columna con `pgcrypto` para campos sensibles si se requiere (no activado en versión académica).

**Cifrado en tránsito:**
- En producción, conexión a PostgreSQL exclusivamente vía TLS (`sslmode=require` en la cadena de conexión).
- En desarrollo local con Docker, comunicación en red interna del contenedor.

**Control de acceso (autenticación y autorización):**
- Usuario `pipeline_user` con permisos completos sobre las tablas del pipeline.
- Rol opcional `telco_analista` (definido como ejemplo en el DDL) con sólo `SELECT` sobre `clientes`; sin `INSERT/UPDATE/DELETE`. Esto permite que analistas consulten para el modelo IA sin riesgo de modificar.
- Principio de mínimo privilegio: cada rol tiene exactamente los permisos que necesita y nada más.

**Gestión de credenciales:**
- Variables de entorno en `.env` (gitignored). Nunca se commitea al repositorio.
- Archivo `.env.example` con valores ficticios para documentar la estructura esperada.
- En producción, las credenciales viven en un gestor (Azure Key Vault, AWS Secrets Manager o HashiCorp Vault).

**Enmascaramiento y anonimización:**
- `customerID` ya viene anonimizado en el dataset (formato `####-AAAAA`, no asociable a un cliente real).
- Si en un dataset real se trabajara con datos identificables, se aplicaría hashing SHA-256 con sal antes de cargar.

**Logging sin PII:**
- Los logs registran conteos, tipos de error y ruta de archivos, pero nunca valores de columnas sensibles (nombre, dirección, número de tarjeta).
- Los rechazos sí guardan el payload completo en JSONB, pero esa tabla tiene control de acceso restringido.

**Auditoría:**
- Tabla `carga_logs` con historial completo de ejecuciones (quién/cuándo/qué/cuántos).
- Tabla `clientes_rechazados` con trazabilidad de calidad de datos.
- Logs en `logs/pipeline_YYYYMMDD.log` rotados diariamente.

**Validación de entrada (anti-inyección):**
- SQLAlchemy usa parámetros bindados, no concatena strings, eliminando riesgos de SQL injection.
- Pandera valida el formato de `customerID` con regex, descartando cualquier intento de inyección por ese campo.

**Backup y recuperación (próximos pasos):**
- Para producción se programaría `pg_dump` diario con retención de 30 días.
- Estrategia 3-2-1: tres copias, dos medios, una offsite.

---

## 6. Documentación del código y evidencias

### 6.1 Recursos en producción

| Recurso | Enlace |
|---|---|
| **Repositorio GitHub (público)** | https://github.com/BenjaminHeresmann/telco-churn-pipeline |
| **API en producción (Railway)** | https://telco-api-production-e466.up.railway.app |
| **Documentación interactiva (Swagger)** | https://telco-api-production-e466.up.railway.app/docs |
| **Health check** | https://telco-api-production-e466.up.railway.app/health |
| **Base de datos** | PostgreSQL 17 gestionado en Supabase (proyecto `telco-churn`) |
| **CI (GitHub Actions)** | Estado verde en `.github/workflows/ci.yml` (pytest en cada push) |

Estructura del repositorio:

```
telco-churn-pipeline/
├── README.md                Guía principal del proyecto
├── Dockerfile               Imagen para Railway (sirve FastAPI con uvicorn)
├── railway.toml             Config de build/deploy/healthcheck de Railway
├── Procfile                 Comando de arranque alternativo
├── requirements.txt         Dependencias Python
├── .env.example             Plantilla de variables sensibles
├── .gitignore / .railwayignore  Exclusiones de git y de deploy
├── .github/workflows/ci.yml CI: pytest en cada push
├── data/
│   ├── source/              Dataset fuente versionado (telco_churn_source.csv)
│   └── raw|clean|validated|rejected/   Zonas de trabajo (efímeras)
├── src/
│   ├── api.py               FastAPI: endpoints REST de cada etapa + orquestador
│   ├── ingesta.py           Etapa 1
│   ├── limpieza.py          Etapa 2
│   ├── validacion.py        Etapa 3
│   ├── carga_bd.py          Etapa 4 (idempotente, engine singleton)
│   ├── run_pipeline.py      Orquestador CLI
│   └── utils/
│       ├── logger.py        Logger centralizado
│       ├── schema.py        Schema pandera + reglas semánticas
│       └── supabase_client.py  Cliente Storage (opcional)
├── sql/
│   └── 01_create_tables.sql DDL Postgres
├── scripts/
│   ├── setup_supabase.py    Aplica DDL en Supabase
│   └── inyectar_errores.py  Dataset roto para demo de rechazos
├── tests/
│   └── test_validaciones.py 6 tests unitarios (corren en CI)
└── docs/
    ├── informe_tecnico.md
    ├── diagramas.md
    ├── presentacion.md
    └── DEPLOY.md
```

### 6.2 Evidencias de ejecución

**Logs de la primera ejecución exitosa (extracto):**

```
2026-05-29 19:03:01 | INFO | ingesta     | Ingesta desde dataset versionado en repo: data/source/telco_churn_source.csv
2026-05-29 19:03:01 | INFO | ingesta     | Ingesta completada | filas=7043 | columnas=21
2026-05-29 19:03:01 | INFO | limpieza    | TotalCharges: 11 celdas vacias convertidas a NaN
2026-05-29 19:03:01 | INFO | limpieza    | TotalCharges: 11 NaN imputados con 0 para clientes con tenure=0 (recien registrados)
2026-05-29 19:03:01 | INFO | limpieza    | Limpieza completada | filas=7043 -> 7043 | nulos=0 | duplicados=0
2026-05-29 19:03:01 | INFO | validacion  | Validacion estructural: 7043 ok, 0 rechazados
2026-05-29 19:03:01 | INFO | validacion  | Validacion semantica:  7043 ok, 0 rechazados
2026-05-29 19:03:03 | INFO | carga_bd    | Tablas de estado vaciadas (full-refresh)
2026-05-29 19:03:03 | INFO | carga_bd    | Insertados 7043 registros en clientes
2026-05-29 19:03:03 | INFO | orquestador | FIN PIPELINE | duracion total = ~2 seg
```

> Nota sobre los 11 registros con `TotalCharges` vacío: son clientes con `tenure=0`
> (recién registrados, sin facturación acumulada todavía). La limpieza los imputa
> con 0 de forma justificada, por lo que los 7.043 registros pasan la validación.
> Si en cambio se ingesta un dataset con errores reales (ver `scripts/inyectar_errores.py`),
> el pipeline los rechaza: ej. `Validacion estructural: 45 ok, 5 rechazados` y
> `Validacion semantica: 42 ok, 3 rechazados`, quedando los 8 inválidos en
> `data/rejected/` y auditados en la tabla `clientes_rechazados`.

**Capturas a incluir en el PDF final:**
1. Terminal con la ejecución completa del orquestador.
2. PostgreSQL psql mostrando `SELECT COUNT(*), churn FROM clientes GROUP BY churn;`
3. Tabla `carga_logs` mostrando los últimos 5 runs.
4. Estructura del repo en GitHub.

### 6.3 Dockerfile y reproducibilidad

El `Dockerfile` parte de `python:3.11-slim`, instala las dependencias del sistema necesarias (`libpq-dev` para psycopg2), copia el código y define el comando por defecto `python src/run_pipeline.py`. El `docker-compose.yml` define dos servicios:

- `postgres`: imagen `postgres:15-alpine` con volumen persistente y healthcheck. Monta `./sql` en `/docker-entrypoint-initdb.d`, ejecutando el DDL automáticamente la primera vez.
- `pipeline`: construido desde el Dockerfile, depende del healthcheck de Postgres, monta `./data` y `./logs` como volúmenes para persistir las salidas. Usa el profile `run` para no ejecutarse automáticamente al hacer `docker compose up`.

Esto garantiza que cualquier evaluador pueda ejecutar el pipeline completo con `docker compose up -d postgres && docker compose run --rm pipeline`.

---

## 7. Estrategia de KPIs de monitoreo

### 7.1 KPIs medidos por ejecución

| KPI | Definición | Umbral de alerta | Dónde se mide |
|---|---|---|---|
| **Latencia total del pipeline** | Segundos desde inicio de ingesta hasta fin de carga | > 30 seg | Orquestador → log + `carga_logs.duracion_segundos` |
| **Latencia por etapa** | Segundos consumidos por cada una de las 4 etapas | Cualquier etapa > 50% del total | Orquestador → log |
| **Volumen procesado** | Número de registros leídos por ejecución | < 5.000 (indica corrupción de fuente) | `carga_logs.registros_leidos` |
| **Tasa de validez estructural** | % de registros que pasan validación pandera | < 95% | Etapa 3 → log |
| **Tasa de validez semántica** | % de registros que pasan reglas de negocio | < 99% | Etapa 3 → log |
| **Completitud por columna** | % de valores no nulos por columna crítica | < 95% en cualquier columna | Etapa 2 → log |
| **Tasa de error en carga** | % de inserts que fallaron por violación de constraint | > 0% | Etapa 4 → `carga_logs.estado` |
| **Estado de ejecución** | OK / PARCIAL / ERROR | Cualquier valor ≠ OK | `carga_logs.estado` |

### 7.2 Mecanismo de alertas

Para la versión académica, las alertas son log-based: cuando un KPI cruza su umbral, el logger escribe a nivel `WARNING` y el operador detecta al revisar el archivo de log. En una versión productiva se conectaría el pipeline a un sistema de monitoreo (Grafana + Prometheus, o servicio cloud equivalente) que envíe alertas a Slack o correo cuando los umbrales se crucen.

### 7.3 Dashboard de seguimiento (próximos pasos)

Se propone una vista SQL agregada sobre `carga_logs` y `clientes_rechazados` que muestre:
- Tendencia diaria de volumen procesado.
- Heatmap de tasa de rechazo por tipo de validación.
- Distribución de duraciones del pipeline.

Esta vista se renderiza luego en una herramienta de BI (Power BI, Metabase o un simple HTML estático generado por el pipeline).

---

## 8. Conclusiones y próximos pasos

### 8.1 Cumplimiento del alcance

El pipeline construido cumple con los cuatro requisitos técnicos definidos por la rúbrica:

1. **Ingesta automatizada** con trazabilidad temporal y logging.
2. **Limpieza y transformación** que resuelve los problemas conocidos del dataset (TotalCharges como string, valores Yes/No no booleanos) y genera la feature derivada `tenure_group`.
3. **Validación estructural y semántica** con pandera y reglas de negocio cruzadas, separando válidos de rechazados con motivos auditables.
4. **Carga a PostgreSQL** transaccional con auditoría completa en `carga_logs` y `clientes_rechazados`.

El sistema es **reproducible** (Docker), **trazable** (logs + auditoría en BD), **seguro** (variables de entorno, control de acceso, cifrado) y **escalable por módulos** (cada etapa puede sustituirse sin afectar a las otras).

### 8.2 Limitaciones reconocidas

- Para volúmenes mucho mayores (>1M filas), la inserción con `to_sql` debería sustituirse por `COPY FROM` directo.
- El pipeline ejecuta secuencialmente; para datasets en paralelo se requeriría un orquestador como Airflow.
- Los KPIs se persisten en BD pero no hay aún dashboard interactivo.

### 8.3 Próximos pasos

**Corto plazo (Evaluación 3):** sobre la tabla `clientes` ya poblada, entrenar un modelo de clasificación binaria (regresión logística o random forest) para predecir `churn`. Las variables candidatas con mayor poder discriminante son `tenure`, `Contract`, `MonthlyCharges`, `InternetService` y `PaymentMethod`.

**Mediano plazo:** conectar el pipeline a una fuente real de la compañía (CRM) reemplazando la etapa de ingesta. Migrar la orquestación a Apache Airflow para soportar dependencias complejas. Implementar el dashboard de KPIs en Power BI o Metabase.

**Largo plazo:** evolucionar a una arquitectura Lakehouse cuando el volumen de datos justifique el costo de un Delta Lake / Iceberg, manteniendo PostgreSQL como capa serving para reportes y BI.

---

**Anexo A — Comandos de ejecución**

```bash
# Setup
git clone https://github.com/<usuario>/telco-churn-pipeline.git
cd telco-churn-pipeline
cp .env.example .env

# Levantar Postgres
docker compose up -d postgres

# Ejecutar pipeline completo
docker compose run --rm pipeline

# Verificar resultados
docker compose exec postgres psql -U pipeline_user -d telco_churn \
  -c "SELECT churn, COUNT(*) FROM clientes GROUP BY churn;"

# Ejecutar tests
pytest tests/ -v
```

**Anexo B — Estructura del dataset**

Ver `0.CASOS_PARCIALES_Evaluaciones-2y3/01_Telco Customer Churn/01_Metadata.txt` y la sección 7 del README del repositorio.
