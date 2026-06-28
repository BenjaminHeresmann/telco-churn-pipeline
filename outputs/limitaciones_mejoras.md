# Limitaciones y propuestas de mejora — Evaluación 3

Caso Telco Churn · ITY1101. Cada limitación se apoya en **evidencia medida** y cada mejora se
clasifica como **preventiva/correctiva** con su **beneficio** (indicadores 4, 5, 7 y 10 ≈ 26%).

## Limitaciones detectadas (con evidencia)

| # | Limitación | Evidencia | Impacto |
|---|---|---|---|
| L1 | **RandomForest sobreajusta** (overfitting) | recall train **100%** / accuracy train 99,2% vs test 64,5% (gap +0,22) | El modelo memoriza; no generaliza a datos nuevos. |
| L2 | **Precisión baja del modelo elegido** | LogReg balanceada: recall 79,7% pero precision **51%** (FP=431) | Muchas falsas alarmas: clientes señalados que no se irían. |
| L3 | **Latencia de red domina el rendimiento** | Lectura nube **3,94s** vs local 0,018s (~219×); entrenamiento 1,34s | El cuello de botella es la conexión a Supabase, no el cómputo. |
| L4 | **Dataset pequeño y desbalanceado** | 7.043 filas, churn 26,5% | Limita la robustez y la generalización del modelo. |
| L5 | **Disponibilidad (free tier)** | Supabase/Railway se suspenden por inactividad | Riesgo operativo para la demo y producción. |
| L6 | **Dependencias con CVEs** | `pip-audit`: 10 CVEs en 3 paquetes (starlette/dotenv/pytest) | Superficie de vulnerabilidad; starlette acoplada a FastAPI. |
| L7 | **Modelo sin optimizar** | Baseline + balanceo; sin tuning de hiperparámetros ni de umbral | Hay margen de mejora no explotado. |

> **Limitación ≠ error:** ninguna de estas es un fallo del sistema; son límites técnicos/operativos
> del alcance actual, conocidos y gestionables.

## Propuestas de mejora (basadas en los hallazgos)

| # | Mejora | Atiende | Tipo | Beneficio esperado |
|---|---|---|---|---|
| M1 | Tunear RandomForest (`max_depth`, `min_samples_leaf`) o regularizar | L1 | Correctiva | Reducir overfitting; mejor generalización. |
| M2 | **Ajustar el umbral de decisión** (no 0,5) según costo FN/FP, o rankear por probabilidad (top-N riesgo) | L2 | Correctiva | Subir precisión sin perder recall; campañas de retención más eficientes. |
| M3 | Acercar cómputo a los datos / cachear lecturas / materializar vistas | L3 | Preventiva | Bajar la latencia dominante (219×). |
| M4 | Validación cruzada k-fold + intervalos de confianza; más *feature engineering* | L4 | Preventiva | Evaluación más robusta y estable. |
| M5 | Keep-alive programado o tier pago | L5 | Preventiva | Disponibilidad garantizada para demo/producción. |
| M6 | Actualizar `python-dotenv`→1.2.2; planear upgrade FastAPI+Starlette | L6 | Correctiva + Preventiva | Cerrar CVEs conocidos. |
| M7 | Conectar el dashboard con el rol `telco_lectura` (solo lectura) | seguridad | Preventiva | Privilegio mínimo en producción (`sql/02_roles_seguridad.sql`). |
| M8 | Exponer el modelo como endpoint `/model/predict` en la API existente | escalado | Preventiva | Scoring on-demand reutilizando la infraestructura cloud. |

## Cómo se implementarían (indicador 10)
Priorización realista para un equipo de 2: **M2 y M1** (mayor impacto en la calidad del modelo, bajo
costo: ya tenemos las probabilidades y el pipeline sklearn) → **M6 y M7** (seguridad, cambios
acotados) → **M3/M5** (rendimiento/disponibilidad, dependen de configuración de la nube) →
**M4/M8** (mejoras mayores de evaluación y arquitectura). Cada una es incremental sobre lo ya
construido, sin rehacer el pipeline.
