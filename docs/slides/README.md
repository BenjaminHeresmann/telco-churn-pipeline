# Presentación de la defensa — Evaluación 2

La presentación está **desplegada en vivo** (12 láminas, formato **4:3**, con la demo funcional del Swagger embebida):

## ▶️ https://telco-churn-defensa.vercel.app

Ábrela en cualquier navegador. Navega con **← / →** (o las miniaturas), **F** para pantalla completa.

> ⚠️ El proyector de la sala es **4:3**; la presentación ya está en ese formato para llenar la pantalla sin franjas negras.

## Estructura (12 láminas · ~15 min)

| # | Lámina | Presenta |
|---|---|---|
| 1 | Portada (integrantes + roles + sección) | Ambos |
| 2 | Necesidad + DataOps vs. tradicional | Benjamín |
| 3 | Arquitectura cloud desacoplada (no monolito) | Diego |
| 4 | El pipeline: ciclo de vida del dato | Benjamín |
| 5 | Metodología PMBOK + Carta Gantt | Diego |
| 6 | Etapas 1–2: Ingesta + Limpieza | Ambos (B → D) |
| 7 | Etapas 3–4: Validación + Carga | Ambos (B → D) |
| 8 | Modelo de datos (ER) | Benjamín |
| 9 | Seguridad + KPIs | Diego |
| 10 | Manejo de anomalías + Escalabilidad | Ambos |
| 11 | Conclusiones y próximos pasos | Ambos |
| 12 | **Demo funcional en vivo** (Swagger) | Ambos |

## Antes de la defensa (checklist)

- [ ] Abrir la presentación en el PC/navegador que se proyectará y probar la navegación.
- [ ] Verificar que la API esté **Online**: https://telco-api-production-e466.up.railway.app/health → debe decir `"status":"healthy"`.
- [ ] Mantener **Supabase activo** (entrar al dashboard el día previo; el plan free pausa por inactividad).
- [ ] Hacer **una corrida previa** de `POST /pipeline/run` para "calentar" Railway antes de la demo.
- [ ] Probar el internet de la sala (la demo en vivo lo necesita). La lámina 12 tiene un botón **"Abrir en pestaña nueva"** por si el `iframe` falla.

## Enlaces del proyecto

- **Presentación:** https://telco-churn-defensa.vercel.app
- **API / Swagger (demo):** https://telco-api-production-e466.up.railway.app/docs
- **Repositorio:** https://github.com/BenjaminHeresmann/telco-churn-pipeline
