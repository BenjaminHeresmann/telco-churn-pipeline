# ✅ Checklist del día de la defensa — Evaluación 3

Guía operativa (qué abrir, en qué orden, qué decir/clickear). El contenido y las
preguntas están en [`guion_defensa.md`](guion_defensa.md).

---

## 🔗 URLs (abrir cada una en una pestaña)

| # | Para | URL |
|---|---|---|
| 1 | **Deck** (la presentación) | https://deck-benjaminheresmanns-projects.vercel.app |
| 2 | **API Swagger** (pipeline, EV2) | https://telco-api-production-e466.up.railway.app/docs |
| 3 | **Trainer Swagger** (entrenar) | https://telco-trainer-production.up.railway.app/docs |
| 4 | **Predictor Swagger** (predecir) | https://telco-predictor-production.up.railway.app/docs |
| 5 | **Dashboard BI** | https://telco-dashboard-production.up.railway.app |
| 6 | Repo GitHub (por si lo piden) | https://github.com/BenjaminHeresmann/telco-churn-pipeline |
| 7 | Supabase (opcional, mostrar tablas) | https://supabase.com/dashboard (login) |

---

## ⏰ 10 MINUTOS ANTES (preparación — CLAVE)

- [ ] **Despertar los servicios** (free tier se duerme): abrir las URLs **1 a 5** una por una. La primera carga tarda ~30s; espera a que cada una responda.
- [ ] En el **Dashboard** (5): abrir **⚙️ Preparar demo → 🧨 Vaciar TODO (modelo + predicciones)** para arrancar **en blanco**.
- [ ] Verificar que el **Deck** (1) abre bien → **F11** (pantalla completa), probar flechas ← →.
- [ ] Dejar las pestañas en orden: Deck · API · Trainer · Predictor · Dashboard.
- [ ] Tener el **guion** a mano (en el celular o impreso).
- [ ] **Plan B listo:** si la red falla, ten capturas de pantalla del dashboard lleno (o pulsa los botones del dashboard en vez del Swagger).

---

## 🎤 EXPOSICIÓN (10 min) — con el Deck

Presentar las **13 láminas** del deck siguiendo el reparto del guion (no leer; preguntas al azar). Cierra la lámina 11 (BI) anunciando: *"ahora lo construimos en vivo"* → pasar a la demo.

---

## 🖥️ DEMO EN VIVO (5 min) — el sistema construyéndose

> Narrativa: **pipeline → entrenar → predecir → el dashboard se llena solo.**
> Tip: ten el **Dashboard** visible en una pestaña; al entrenar/predecir desde los Swagger, **se actualiza solo** (auto-refresh cada 3s).

### Paso 1 · Pipeline (Fase 1) — pestaña **API Swagger** (1,5 min)
- [ ] `POST /pipeline/run` → **Execute**.
- 💬 *"Este es el pipeline de Eval 2: ingesta, limpieza, validación y carga. Deja 7.043 clientes limpios en Supabase — la base de datos del sistema."*

### Paso 2 · Entrenar — pestaña **Trainer Swagger** (1,5 min)
- [ ] `POST /train` → **Execute** → responde con `recall ≈ 0.797`.
- 💬 *"Este es un microservicio SEPARADO que entrena el modelo y lo guarda en Supabase. Es la mejora que pidió el profe: contenedores separados por responsabilidad, ahora en la capa de IA."*
- [ ] Pasar a la pestaña **Dashboard** → **aparecen solas las métricas** (recall 79,7%, matriz de confusión, variables).
- 💬 *"Apenas entrenó, el dashboard muestra las métricas. Pero todavía no puntuamos a los clientes (0 en riesgo)."*

### Paso 3 · Predecir — pestaña **Predictor Swagger** (2 min)
- [ ] `POST /predict/batch` → **Execute** → `7043 puntuados, 2914 en riesgo`.
- [ ] (Opcional, impactante) `GET /predict/cliente/{customer_id}` con `7590-VHVEG` → churn 82%.
- 💬 *"Otro microservicio: carga el modelo ya entrenado y predice, SIN re-entrenar (train ≠ predict)."*
- [ ] Pasar a la pestaña **Dashboard** → **se llena solo**: clientes en riesgo, tabla filtrable de errores, segmentos, embudo.
- 💬 *"El dashboard es la capa BI: la cara visible donde las predicciones se vuelven decisiones de retención."* → filtrar **Falsos Negativos** y comentar un caso.

### Cierre
- 💬 *"Pipeline, entrenamiento, predicción y dashboard: cuatro servicios independientes, comunicándose por Supabase, construidos en vivo."*

---

## ❓ Preguntas (60% individual) → ver `guion_defensa.md`
Foco: **métricas del modelo** (ind.8) y **seguridad + Ley 21.719** (ind.9). Ambos deben poder responder cualquier parte.

---

## 🔻 DESPUÉS de la evaluación (seguridad)
- [ ] **Revocar los tokens:** Supabase, Railway, Vercel.
- [ ] (Opcional) Pausar/eliminar los proyectos Railway (api, dashboard, trainer, predictor) y reactivar tus otros proyectos Supabase.

---

### Si algo falla (plan B rápido)
- **Un servicio no responde** → estaba dormido; recárgalo y espera ~30s.
- **El dashboard no se actualiza solo** → pulsa **🔄 Actualizar** o el botón **▶ Ejecutar predicción** del propio dashboard.
- **No hay red** → muestra las capturas del dashboard lleno y explica el flujo con el deck.
