# Diseño — Predicción de cliente nuevo (demo en vivo)

**Fecha:** 2026-06-30 · **Ramo:** ITY1101 Gestión de Datos para IA (Duoc UC) · **Evaluación 3**

## Problema

El demo actual (`POST /predict/batch`) puntúa **toda la base** de clientes — la misma
con la que se entrenó el modelo final (re-ajustado sobre el 100% de los datos
etiquetados). Las métricas del informe son honestas (salen del holdout 30%), pero
el *scoring en vivo* sobre la base completa es rendimiento de entrenamiento, no de
generalización. Para la defensa queremos **predecir sobre clientes que el modelo
nunca vio**, de forma tangible e interpretable.

## Objetivo

Permitir predecir el riesgo de churn de **un cliente individual inventado en vivo**,
armado desde el dashboard, mostrando el % de riesgo **y el porqué** (factores que
empujan a la fuga / que retienen). Sin reentrenar. Reutilizando el pipeline existente.

## Enfoque elegido

**Endpoint nuevo en el microservicio predictor + formulario en el dashboard que lo
consume.** Coherente con la arquitectura de microservicios desacoplados (dashboard =
capa BI, predictor = modelo). Descarta predecir localmente en el dashboard (acoplaría
la capa BI al modelo) y un script aparte (no es demo en vivo).

## Componentes

### 1. `src/modelo.py`
- `CLIENTE_TEMPLATE: dict` — plantilla con los 19 predictores (nombres de esquema CSV),
  con defaults reales del dataset (modas categóricas / medianas numéricas):
  gender=Male, SeniorCitizen=0, Partner/Dependents=False, tenure=29, PhoneService=True,
  MultipleLines=No, InternetService=Fiber optic, servicios=No, Contract=Month-to-month,
  PaperlessBilling=True, PaymentMethod=Electronic check, MonthlyCharges=70.35,
  TotalCharges autocalculado ≈ tenure×MonthlyCharges.
- `predecir_cliente_nuevo(pipe, datos: dict) -> dict` — superpone `datos` sobre la
  plantilla, arma un DataFrame de 1 fila (binarias→int, categóricas→str), llama a
  `predecir_df`, y añade `nivel_riesgo` (alto ≥0.5 / medio ≥0.3 / bajo) + `explicar_prediccion`.
- `explicar_prediccion(pipe, X_row) -> dict` — interpretabilidad honesta de la LogReg:
  `contrib = clf.coef_ × pre.transform(X_row)` por variable; mapea nombres técnicos
  (`cat__Contract_Month-to-month`) a español; devuelve top-4 que empujan a fuga
  (contrib>0) y top-2 que retienen (contrib<0). Sin dependencias nuevas (numpy).

### 2. `src/serve_modelo.py` (rol predictor)
- Modelo Pydantic `ClienteNuevo(BaseModel)` con todos los campos **opcionales** (defaults
  None) → Swagger muestra el esquema. `POST /predict/nuevo` overlaya lo enviado sobre la
  plantilla y responde:
  ```json
  { "probabilidad_churn": 0.82, "churn_predicho": true, "nivel_riesgo": "alto",
    "factores": { "empujan_a_fuga": [{"factor":"Contrato: Mes a mes","peso":0.91}],
                  "retienen": [{"factor":"Soporte técnico: Sí","peso":-0.30}] },
    "modelo": "LogReg balanceada",
    "nota": "Cliente no presente en la base — predicción sobre datos no vistos." }
  ```

### 3. `dashboard/app.py`
- Sección **"🔮 Predecir un cliente nuevo"** (expander tras el panel de demo).
- Helper `_post_json(url, payload)` (POST con cuerpo; hoy solo hay `_post` sin cuerpo).
- **Presets** ("Cliente de alto riesgo" / "Cliente fiel") que rellenan `st.session_state`.
- ~10 controles clave (Contract, tenure, MonthlyCharges, InternetService, PaymentMethod,
  TechSupport, OnlineSecurity, PaperlessBilling, Partner/Dependents, SeniorCitizen); resto
  por defecto.
- Botón "Predecir" → `POST {PREDICTOR_URL}/predict/nuevo` → **gauge Plotly** (go.Indicator)
  con el %, etiqueta de nivel, y los factores del "por qué". Cartel: *"Este cliente NO está
  en la base — el modelo nunca lo vio."*

## Datos / contrato

- Entrada admite parcial: lo no enviado se completa con `CLIENTE_TEMPLATE`.
- Binarias (Partner, Dependents, PhoneService, PaperlessBilling, SeniorCitizen) → int 0/1.
- `OneHotEncoder(handle_unknown="ignore")` tolera valores no vistos → nunca rompe.
- No escribe en Supabase (es una predicción efímera de demo, sin etiqueta real).

## Manejo de errores

- Predictor sin modelo → 503 (igual que `/metrics`).
- Campo con valor fuera de dominio → predice igual (ignore) ; el dashboard limita las
  opciones a los dominios reales, así que no ocurre desde la UI.

## Pruebas

1. Local: cargar el pipeline desde Supabase, `predecir_cliente_nuevo` con preset alto
   riesgo (esperado ≳0.7) y fiel (esperado ≲0.15); verificar que los factores tienen
   sentido y `peso` coherente con el signo.
2. Endpoint desplegado (Railway): `curl POST /predict/nuevo` con ambos presets.
3. Dashboard en Chrome: presets + un cliente a mano; gauge y factores correctos.

## Despliegue

- Redespliegue del **predictor** a Railway (imagen ya tiene sklearn/pandas/fastapi; sin
  deps nuevas). El trainer no cambia. El dashboard se redespliega (Streamlit/host actual).

## Fuera de alcance (YAGNI)

- Predicción por lote de archivo, persistencia del cliente inventado, edición de todos
  los 19 campos en la UI, otros modelos. Solo cliente individual + porqué.

## Valor para la defensa

Responde de frente a *"predijeron sobre datos de entrenamiento"*: predicción en vivo
sobre un cliente jamás visto **+** interpretabilidad (generalización e interpretabilidad
en una pantalla).
