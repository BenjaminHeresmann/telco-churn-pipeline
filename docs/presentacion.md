# Esqueleto de Presentación — Defensa Evaluación 2

**Duración total:** 20 minutos (15 min presentación + demo + 5 min preguntas)
**Equipo:** Benjamín y Diego (división equitativa, ~10 min cada uno)
**Apoyo recomendado:** PowerPoint, Canva o Google Slides
**Tip:** no leer las slides; usarlas como apoyo visual

---

## Slide 1 — Portada (30 seg)
**Quién habla:** Benjamín

- Título: "Pipeline DataOps para Predicción de Churn en Telco"
- Asignatura: ITY1101 Gestión de Datos para IA
- Integrantes: Benjamín Heresmann · Diego Hernández
- Fecha: 2 de junio de 2026

**Qué decir:** Saludo breve, presentación del nombre del proyecto, mencionar que en los próximos 15 min se mostrará el ciclo completo de DataOps aplicado a un caso real de telecomunicaciones, con demo en vivo del pipeline funcionando.

---

## Slide 2 — Presentación del equipo y roles (1 min)
**Quién habla:** Diego

- Benjamín: Ingesta + Validación + Diagramas + Sección informe Pipeline
- Diego: Limpieza + Carga BD + Plan Seguridad + KPIs
- Ambos: Orquestador, tests, demo, defensa

**Qué decir:** Cada uno asumió responsabilidad técnica sobre etapas específicas pero ambos manejan el sistema completo. La idea es que cualquier pregunta del docente la pueda responder cualquiera de los dos.

---

## Slide 3 — El problema de negocio (1 min)
**Quién habla:** Benjamín

- Una empresa de telecomunicaciones pierde clientes (churn ≈ 26%)
- Cada cliente perdido = ingresos recurrentes que desaparecen
- Para retener hay que **anticipar** quién va a irse
- Para anticipar hay que tener **datos limpios, confiables y trazables**

**Qué decir:** Sin datos de calidad no hay modelo de IA que funcione. Por eso DataOps es el cimiento de cualquier proyecto analítico serio. Este pipeline es lo que habilita la predicción.

**Visual sugerido:** gráfico de pie 73.5% No Churn / 26.5% Churn

---

## Slide 4 — ¿Por qué DataOps vs. enfoque tradicional? (1 min)
**Quién habla:** Benjamín

| Enfoque tradicional | DataOps |
|---|---|
| Excel manual, copy-paste | Scripts automatizados |
| Errores invisibles | Logs y validaciones explícitas |
| Una persona sabe cómo correrlo | Cualquiera lo levanta con Docker |
| Sin versionado | Git + GitHub |
| Sin trazabilidad | Cada ejecución queda registrada |

**Qué decir:** DataOps no es solo automatizar; es construir un sistema que cualquier integrante del equipo (o el evaluador) pueda reproducir end-to-end, con visibilidad de qué pasó en cada ejecución.

---

## Slide 5 — Metodología PMBOK aplicada (1 min)
**Quién habla:** Diego

- Enfoque **híbrido** (predictivo + adaptativo)
- Predictivo: BD, Dockerfile, integración GitHub (requisitos fijos)
- Adaptativo: reglas semánticas, KPIs, demo (descubrimiento iterativo)
- Seguimiento: Trello (kanban Por hacer / En progreso / Terminado)

**Qué decir:** Una metodología puramente cascada sería rígida; una puramente ágil sería caótica para coordinar dependencias técnicas. El híbrido permite planificar lo estable y descubrir lo exploratorio.

---

## Slide 6 — Carta Gantt / WBS (1 min)
**Quién habla:** Diego

- Mostrar carta Gantt con 4 fases: Setup, Pipeline, Documentación, Defensa
- Hitos: H1 stack funcional, H2 pipeline end-to-end, H3 documentación completa
- Equipo de 2 personas con división clara de responsabilidades

**Visual sugerido:** captura del diagrama 5 de `docs/diagramas.md` (Gantt en Mermaid)

---

## Slide 7 — Arquitectura del pipeline (1.5 min)
**Quién habla:** Benjamín

- Pipeline Modular Lineal con 4 etapas:
  1. Ingesta → `data/raw/`
  2. Limpieza/Transformación → `data/clean/`
  3. Validación → `data/validated/` + `data/rejected/`
  4. Carga → PostgreSQL
- Capas transversales: logger, variables de entorno, KPIs

**Visual:** captura del diagrama 1 de `docs/diagramas.md` (arquitectura)

**Qué decir:** Cada etapa es independiente, ejecutable por separado y con responsabilidad acotada. Si una falla, las anteriores ya dejaron su salida en disco y el operador puede retomar desde ahí.

---

## Slide 8 — Etapa 1: Ingesta (45 seg)
**Quién habla:** Benjamín

- Lee CSV fuente (ruta en `.env`)
- Copia a `data/raw/` con sello temporal
- Log: filas leídas, columnas, ruta destino

**Justificación clave:** ingesta batch (no streaming) porque el caso es analítico, no transaccional. Streaming sería sobreingeniería.

---

## Slide 9 — Etapa 2: Limpieza y transformación (1 min)
**Quién habla:** Diego

- Resuelve el bug clásico del dataset: `TotalCharges` como string con vacíos
- Imputación inteligente: si `tenure=0`, `TotalCharges=0` (cliente nuevo)
- Convierte Yes/No a booleano en columnas binarias claras
- Crea feature derivada `tenure_group` (5 bins)
- Elimina duplicados por `customerID`

**Qué decir:** la limpieza no decide qué es válido (eso es la siguiente etapa); solo normaliza para que la validación pueda trabajar.

---

## Slide 10 — Etapa 3: Validación (1.5 min)
**Quién habla:** Benjamín

**Estructural (pandera):**
- Tipos, rangos, valores permitidos, regex de `customerID`
- 22 columnas validadas

**Semántica (Python puro):**
- Coherencia internet: `InternetService=No` ↔ servicios derivados `"No internet service"`
- Coherencia telefonía: `PhoneService=False` ↔ `MultipleLines="No phone service"`
- Coherencia financiera: `TotalCharges ≥ 0.5 × MonthlyCharges × 1` (margen descuentos)

**Resultado:** válidos → `data/validated/`; rechazados → `data/rejected/` con motivo.

---

## Slide 11 — Etapa 4: Carga a PostgreSQL (1 min)
**Quién habla:** Diego

- SQLAlchemy + psycopg2 para conexión
- Inserción transaccional (rollback ante fallo)
- Auditoría en `carga_logs` (archivo, conteos, duración, estado)
- Rechazados auditados en `clientes_rechazados` con payload JSONB

**Qué decir:** la BD no es solo destino, es también la fuente de verdad para preguntas como "¿cuántas veces ha corrido el pipeline esta semana?" o "¿qué tipo de error rechaza más registros?".

---

## Slide 12 — Plan de Seguridad DataOps (1.5 min)
**Quién habla:** Diego

**Legal:** Ley 19.628 (Chile) protección datos personales, Ley 21.459 delitos informáticos

**Técnicas implementadas:**
- Cifrado en reposo (volumen Docker + disco cifrado SO)
- Cifrado en tránsito (TLS para Postgres)
- Control de acceso (rol `telco_analista` solo SELECT, principio mínimo privilegio)
- Variables de entorno (`.env` gitignored) → cero credenciales en código
- Logs sin PII (conteos y errores, no valores sensibles)
- Anti-inyección (SQLAlchemy bindea parámetros)
- Auditoría completa (tabla `carga_logs`)

**Próximos pasos:** integración con secret manager (Vault/Key Vault), backup automatizado.

---

## Slide 13 — KPIs de monitoreo (1 min)
**Quién habla:** Diego

| KPI | Umbral alerta |
|---|---|
| Latencia total pipeline | > 30 seg |
| Tasa de validez estructural | < 95% |
| Tasa de validez semántica | < 99% |
| Volumen procesado | < 5.000 filas |
| Estado de ejecución | ≠ OK |

Persistencia: tabla `carga_logs`. Alertas vía log `WARNING`. Próximo paso: dashboard Grafana o Power BI.

---

## Slides 14-18 — DEMO EN VIVO (5 min)
**Quién habla:** alternancia

**Setup previo:**
- Terminal abierto en la raíz del proyecto
- Docker Desktop corriendo (si se usa Docker)
- Postgres ya levantado (`docker compose up -d postgres`)
- Carpeta `data/raw/` vacía para que se vea la magia

**Guion de la demo:**

### Demo paso 1 (1 min) — "Ejecutamos el pipeline completo"
```bash
.venv\Scripts\activate
python src/run_pipeline.py
```
- Mostrar los logs corriendo en orden
- Resaltar: "FIN PIPELINE | duracion = X seg"

### Demo paso 2 (1 min) — "Veamos los datos en la BD"
```bash
docker compose exec postgres psql -U pipeline_user -d telco_churn -c "SELECT churn, COUNT(*) FROM clientes GROUP BY churn;"
docker compose exec postgres psql -U pipeline_user -d telco_churn -c "SELECT * FROM carga_logs ORDER BY fecha_ejecucion DESC LIMIT 3;"
```

### Demo paso 3 (2 min) — "Y ahora veamos qué pasa con datos rotos"
```bash
python scripts/inyectar_errores.py
# Editar src/run_pipeline.py o usar un script auxiliar para apuntar al dataset roto
python -c "import sys; sys.path.insert(0,'src'); from limpieza import limpiar; from validacion import validar; from pathlib import Path; ruta_clean = limpiar(Path('data/raw/telco_churn_demo_con_errores.csv')); validar(ruta_clean)"
```
- Mostrar los logs `WARNING` detectando 5 errores estructurales + 3 semánticos
- Abrir el archivo de rechazados y mostrar los motivos

### Demo paso 4 (1 min) — "Y los rechazos quedan auditados en BD"
```bash
docker compose exec postgres psql -U pipeline_user -d telco_churn -c "SELECT customer_id, motivo_rechazo, tipo_validacion FROM clientes_rechazados;"
```

---

## Slide 19 — Conclusiones y próximos pasos (1 min)
**Quién habla:** Benjamín

**Logros:**
- Pipeline funcional end-to-end con 4 etapas
- Reproducible (Docker), trazable (logs+BD), seguro (cifrado+control acceso)
- Tests unitarios sobre reglas semánticas
- 8 tipos de errores intencionalmente detectados en demo

**Próximos pasos:**
- Evaluación 3: entrenar modelo de clasificación binaria sobre `clientes.churn`
- Variables candidatas: `tenure`, `Contract`, `MonthlyCharges`, `InternetService`
- Migrar orquestación a Airflow cuando se conecten múltiples fuentes
- Dashboard de KPIs en Grafana o Power BI

---

## Slide 20 — Preguntas (5 min)
**Quién habla:** ambos según pregunta

**Preparados para responder:**
- ¿Por qué pandera y no Great Expectations? *(simplicidad + integración pandas)*
- ¿Cómo escalarían a 100M filas? *(COPY directo + Spark + particionado)*
- ¿Qué pasa si Postgres está caído? *(rollback automático, log de error, retry policy)*
- ¿Por qué imputan TotalCharges con 0? *(análisis del dataset mostró que los 11 nulos son tenure=0, justificable)*
- ¿Cómo aseguran reproducibilidad? *(Docker + requirements.txt fijo + variables entorno + DDL versionado)*
- ¿Y la calidad del dataset con el tiempo? *(tabla carga_logs permite trending de tasa de rechazos)*
- ¿Por qué metodología híbrida y no scrum puro? *(equipo de 2, duración corta, dependencias técnicas mixtas)*

---

## Checklist pre-presentación (último día)

- [ ] Repo en GitHub público (o privado con acceso al docente)
- [ ] README en español y entendible por un tercero
- [ ] Capturas de los logs y de queries SQL en el informe PDF
- [ ] Diagramas exportados a PNG e insertados en el informe
- [ ] Docker Desktop corriendo y testeado mínimo 1 vez antes de la demo
- [ ] `.env` configurado y datos cargados al menos una vez
- [ ] Script `inyectar_errores.py` probado
- [ ] Slides exportadas a PDF como respaldo
- [ ] Backup del proyecto en USB por si falla la red
- [ ] Ensayo cronometrado de los 15 min con los dos integrantes

---

## Tips para la defensa individual (70% de la nota)

1. **Mira al docente, no a la pantalla.** Las slides son apoyo, no guion.
2. **Si no sabes algo, di "esa decisión la tomamos por X razón, déjeme mostrar dónde está en el código"** y muestra el archivo. Mejor honestidad técnica que invento.
3. **Tener el repo abierto en VS Code** durante toda la presentación para poder mostrar código rápidamente.
4. **Para preguntas sobre alternativas tecnológicas**, siempre mencionar al menos una alternativa que evaluaron y por qué eligieron la actual.
5. **Para preguntas sobre escalabilidad**, mencionar siempre 3 cosas: paralelización (Spark), particionado (Postgres), y caching (Redis o materialized views).
6. **Practicar la transición** entre quien presenta — silencios incómodos restan puntos.
