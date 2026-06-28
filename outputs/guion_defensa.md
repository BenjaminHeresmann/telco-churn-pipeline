# Guion de defensa — Evaluación 3 (15 min = 10 expo + 5 demo)

**Reparto alternado y equitativo.** Regla de oro: **ambos dominan TODO** (el docente pregunta al
azar a cualquiera). El reparto es solo para la exposición; las preguntas individuales (70%) pueden
ir a cualquiera. **No leer las slides.**

## Exposición (10 min)

| Tiempo | Bloque | Quién | Puntos clave |
|---|---|---|---|
| 0:00–1:15 | **Apertura + Resumen Fase 1** | Benjamín | Caso Telco Churn, equipo, PMBOK. Qué entregó el Parcial 2: pipeline DataOps de 4 etapas, cloud desacoplado (GitHub·Railway·Supabase), **7.043 clientes limpios** en PostgreSQL. Mejora del docente: contenedor por capa. |
| 1:15–2:45 | **Calidad de datos + EDA** | Diego | 7.043 filas, **0 nulos**, **desbalance 26,5%**. Bivariado: Month-to-month **42,7%**, tenure 0–12 **47,4%**, fibra **41,9%**, electronic check **45,3%**. Matriz de correlación (tenure ↓ churn). |
| 2:45–4:45 | **Modelo: diseño y entrenamiento** | Benjamín | Clasificación binaria supervisada, target `churn`. **Recall prioritario** (FN = cliente que se va sin detectar = error más caro). Split **70/30 estratificado**. Baseline (LogReg, Árbol) → mejora (RF, LogReg balanceada) con `class_weight`. |
| 4:45–6:30 | **Métricas e interpretación** | Diego | Matriz de confusión. **Recall 79,7%** (detecta 447/561). Accuracy 74,2% **engaña** (todo "No-churn" daría 73,5%). **Gini 0,69**, ROC-AUC 0,85. **Overfitting** del RF (train 100% / test 63,5%). |
| 6:30–8:15 | **Seguridad + Ley 21.719** | Benjamín | 4 frentes: 0 secretos (grep+git), **RLS cerrado por defecto**, pip-audit (10 CVEs), logs. Privilegio mínimo (rol solo-lectura). **Compliance by design** hacia la Ley 21.719 (nivel GDPR, vigencia 01-12-2026). |
| 8:15–10:00 | **Rendimiento + Limitaciones/mejoras** | Diego | Benchmark: **cuello de botella = latencia de red** (3,9s nube vs 0,018s local), no el cómputo. Limitaciones (overfit RF, precisión baja, latencia) → mejoras priorizadas (ajuste de umbral, regularizar, actualizar deps). |

## Demo en vivo (5 min) — alternando
**ANTES:** despertar Railway + Supabase + tener `localhost:8501` abierto y probado. Plan B: capturas.

1. **(1 min) Pipeline en producción** — Swagger en Railway (`/docs`): mostrar los endpoints; opcional `POST /pipeline/run` → 4 etapas OK, 7.043 cargados.
2. **(1 min) Datos + predicciones en Supabase** — tabla `clientes` (7.043) y tabla `predicciones` (2.113 con probabilidad/clase/acierto).
3. **(3 min) Dashboard BI** (`streamlit run dashboard/app.py`) — KPIs (recall 79,7%), **matriz de confusión** interactiva, **tabla filtrable de errores** (filtrar Falsos Negativos), **embudo de volumen por etapa**. Cerrar conectando un hallazgo del dashboard con una decisión de retención.

---

## Preguntas anticipadas (el 60% individual: ind.8 métricas + ind.9 seguridad)

**Modelo / métricas (ind.8, 30%):**
- *¿Por qué recall y no accuracy?* → Desbalance 26,5%; accuracy engaña; el FN (no detectar un abandono) es el error más costoso en retención.
- *¿Qué es la matriz de confusión / un FN aquí?* → TP/TN/FP/FN; FN = cliente que se va y el modelo dijo que no.
- *¿Qué es el Gini?* → Gini = 2·AUC−1; mide poder discriminante; 0,69 = bueno, lejos del azar (0).
- *¿Qué es overfitting y dónde lo vieron?* → Alto en train / bajo en test; el RF: recall 100% train vs 63,5% test.
- *¿Por qué estratificar el split?* → Mantener la proporción de clases en train y test (clave con desbalance).
- *¿Variable objetivo vs predictoras?* → Objetivo = `churn` (lo que se predice); predictoras = atributos del cliente.
- *¿Por qué `class_weight` y no SMOTE?* → Desbalance moderado; una línea, sin datos sintéticos ni riesgo de fuga.

**Seguridad / Ley (ind.9, 30%):**
- *¿Qué ley aplica?* → Ley 19.628 modernizada por la **21.719** (nivel GDPR, vigencia plena 01-12-2026); diseño *compliance by design*.
- *¿Qué datos personales hay? ¿sensibles?* → Personales (género, edad, situación familiar, económicos); **no** sensibles en sentido estricto.
- *¿Cómo aplican privilegio mínimo?* → Rol dueño para el pipeline; rol **solo-lectura** para dashboard/analítica; RLS cerrado para roles públicos.
- *¿Accesos fallidos repetidos en los logs?* → Posible **fuerza bruta**; se monitorean como evento de seguridad.
- *¿Cómo evitan secretos en el repo?* → `.env` gitignored, variables de entorno; verificado con grep + historial git (0 filtraciones).
- *¿Qué es trivy / pip-audit?* → Escáneres de vulnerabilidades (imágenes/dependencias); pip-audit halló 10 CVEs con plan de actualización.

**Mejoras (ind.10, 10%):** tener listas 2-3 mejoras con *cómo* implementarlas (ajuste de umbral, regularizar RF, actualizar `python-dotenv`).
