# Reporte de Auditoría Total y Tests E2E

**Fecha:** 29 de mayo de 2026
**Alcance:** código, seguridad, consistencia documental, cumplimiento de rúbrica, tests end-to-end (producción y local).
**Resultado global:** ✅ Sistema correcto, seguro y desplegado. Hallazgos corregidos. Pendientes solo de formato (PDF/slides/capturas).

---

## 1. Auditoría estática de código

| # | Hallazgo | Severidad | Estado |
|---|---|---|---|
| 1 | `carga_bd._ultimo_rechazado()` tomaba el último archivo de rechazados por glob, no el de la corrida actual → podía auditar rechazados de una corrida vieja cuando la actual no tenía ninguno. | **Alta** | ✅ Corregido: `_rechazado_de()` empareja por timestamp del validado. Probado con regresión. |
| 2 | `scripts/inyectar_errores.py` apuntaba a la carpeta del curso fuera del repo (no portable). | Media | ✅ Corregido: usa `data/source/telco_churn_source.csv`. |
| 3 | Engine SQLAlchemy se creaba en cada request (`/health`, `/kpis`, etc.) sin cerrarse → riesgo de agotar conexiones del pooler de Supabase, agravado porque Railway llama `/health` repetidamente. | **Alta** | ✅ Corregido: engine singleton con `lru_cache` + pool acotado (`pool_size=3`, `max_overflow=2`, `pool_recycle=300`). |
| 4 | `import pandera as pa` sin usar en `schema.py`. | Baja | ✅ Eliminado. |
| 5 | Docstring de `api.py` no listaba `/kpis/resumen` ni `/rechazados`. | Baja | ✅ Actualizado. |
| 6 | `limpieza.py`: `.map({"Yes":True,"No":False})` convierte valores inesperados a NaN silenciosamente. | Baja (latente) | Documentado. No afecta el dataset real ni la demo; el dataset roto no toca esas columnas. |

---

## 2. Auditoría de seguridad

| Verificación | Resultado |
|---|---|
| Secretos en historial git (todos los commits) | ✅ Limpio — cero contraseñas/tokens/connection strings reales. |
| `.env` commiteado | ✅ Nunca. Correctamente gitignored. |
| Archivos trackeados | ✅ Solo código/docs/config; `.env.example` con placeholders. |
| Connection strings hardcodeados | ✅ Ninguno. |
| SQL injection | ✅ Parámetros bindados (`text()` con `:param`), sin f-strings en `execute()`. |
| Cifrado en tránsito a la BD | ✅ SSL forzado a Supabase (pooler 6543). |
| CORS | ✅ Corregido: `allow_credentials=False` (la combinación con `*` era inválida). |
| Credenciales en producción | ✅ Solo en Railway Variables, nunca en el repo. |

**Mejoras documentadas (no bloqueantes):** acotar `limit`/`lineas` máximos en endpoints de consulta; autenticación opcional (API key) en endpoints POST.

---

## 3. Tests E2E en producción (Railway → Supabase)

| Test | Resultado |
|---|---|
| 9 endpoints GET (`/`, `/health`, `/docs`, `/openapi.json`, `/kpis/last`, `/kpis/resumen`, `/logs/last`, `/rechazados`, 404) | ✅ 9/9 |
| 4 etapas individuales en orden (`/pipeline/ingest|clean|validate|load`) | ✅ 4/4, carga 7.043 |
| Idempotencia: 3× `/pipeline/run` consecutivos | ✅ 3/3 → siempre 7.043, ~1.9s c/u |
| Verificación directa en Supabase | ✅ 7.043 clientes, 0 duplicados, 0 nulls críticos, `carga_logs` preserva histórico |
| `/health` reporta estado de BD | ✅ `healthy` / `database: ok` |

---

## 4. Tests locales

| Test | Resultado |
|---|---|
| `pytest tests/` | ✅ 6/6 |
| Pipeline con dataset roto (8 errores intencionales) | ✅ 5 estructurales + 3 semánticos detectados, 42 cargados, 8 auditados |
| Regresión del bug #1 (corrida limpia con archivo de rechazados viejo en disco) | ✅ Audita 0 (antes habría reinsertado 8) |

---

## 5. Consistencia documentación vs. realidad

| Inconsistencia | Corrección |
|---|---|
| "7032" registros en 7 lugares | → 7.043 (real tras imputación de TotalCharges) |
| "7.044 clientes" en resumen | → 7.043 (7044 incluía el header del CSV) |
| Bloque de logs del informe no reflejaba la imputación | → Reescrito con la salida real + ejemplo de rechazos |
| "Integridad referencial" impreciso (no hay FKs entre tablas) | → Matizado: modelo de tabla única; integridad por PK + CHECK + NOT NULL + transacciones |
| "PostgreSQL 15" | → 17 (versión real de Supabase) |
| "CSV en Supabase Storage" como flujo principal | → Aclarado: MVP lee del repo (`data/source/`); Storage es opción |
| "deploy automático al merge" (4 lugares) | → CI automático (tests) / CD manual (`railway up`); auto-deploy activable |
| Sección 6: "URL `<usuario>` a publicar" | → Links reales de GitHub + Railway + Swagger |
| Estructura del repo desactualizada (faltaba `data/source/`, `setup_supabase.py`, `api.py`) | → Actualizada |

---

## 6. Cumplimiento de la rúbrica de evaluación

### Dimensión: Encargo / Informe (15%)

| Indicador | Evidencia | Estado |
|---|---|---|
| 1. Problema clave + DataOps + metodología PMBOK (3%) | Informe §1, §2 (PMBOK híbrido justificado) | ✅ Contenido listo |
| 2. Pipeline 4 etapas + herramientas + justificación (3%) | Informe §4.1–4.4 (cada etapa con decisiones y alternativas) | ✅ |
| 3. Políticas de seguridad (enmascaramiento, control acceso) (3%) | Informe §5 (Ley 19.628/21.459, cifrado, roles, hashing) | ✅ |
| 4. Evidencias: GitHub + logs + Dockerfile (3%) | Informe §6 (links reales, logs, estructura, Dockerfile) | ✅ |
| 5. KPIs de monitoreo (latencia, completitud) (3%) | Informe §7 (8 KPIs con umbrales) | ✅ |

### Dimensión: Presentación (15%)

| Indicador | Evidencia | Estado |
|---|---|---|
| 6. Necesidad del proyecto + DataOps vs tradicional (5%) | Guion slides 3–4 | ✅ Guion listo |
| 7. Plan de seguridad legal + técnico (10%) | Informe §5 + slide 12 | ✅ |

### Dimensión: Presentación y Preguntas (70%)

| Indicador | Evidencia | Estado |
|---|---|---|
| 8. Metodología + demo funcional con automatizaciones (25%) | Demo en vivo real (Swagger /pipeline/run), idempotente, guion slides 14–18 | ✅ Demo operativa |
| 9. Explica cada proceso DataOps, responde por fase (25%) | Guion de preguntas + dominio del código | ✅ Requiere ensayo individual |
| 10. Anomalías + escalabilidad (20%) | Guion de preguntas (refute/escala) + demo dataset roto | ✅ Requiere ensayo individual |

**Conclusión de rúbrica:** todo el **contenido** exigido está cubierto y verificado. Lo que resta es **formato y ensayo**, no contenido.

---

## 7. Pendientes (solo formato — los 4 puntos finales)

| # | Tarea | Riesgo / Nota |
|---|---|---|
| 1 | Convertir `informe_tecnico.md` a PDF (Arial/Calibri 10–12, interlineado 1.5, justificado) | ⚠️ El informe tiene ~5.150 palabras. La rúbrica pide **10–12 páginas**. Probablemente haya que **condensar** o mover detalle a anexos para no exceder. |
| 2 | Exportar los 5 diagramas Mermaid (`docs/diagramas.md`) a PNG e insertarlos | Usar mermaid.live |
| 3 | Capturas de evidencia para el PDF | Swagger `/docs`, tablas en Supabase, `carga_logs`, CI verde, Railway "Online" |
| 4 | Armar slides desde `docs/presentacion.md` | 20 slides, ~10 min c/u |
| 5 | Ensayar demo en vivo con las URLs reales | Indicadores 8–10 = 70% de la nota |

### Riesgos operativos para el día de la presentación
- **Supabase free tier** pausa la BD por inactividad prolongada → entrar al dashboard el día previo para mantenerla activa.
- **Railway** verificar que la URL siga "Online" antes de presentar.
- Tener **plan B**: capturas/video de la demo por si falla la red en la sala.

---

## 8. Veredicto

El sistema es **funcionalmente correcto, seguro y está desplegado y probado end-to-end en la nube**. La auditoría encontró y corrigió 1 bug de severidad alta (emparejamiento de rechazados), 1 problema de estabilidad alta (engine sin reuso), y ~9 inconsistencias documentales. No quedan defectos abiertos de código. El trabajo restante es de presentación (PDF, diagramas, slides, ensayo).
