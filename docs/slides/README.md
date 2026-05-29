# Slides de la defensa — Evaluación 2

Presentación en **reveal.js** (HTML), self-contained, con demo embebida del Swagger en vivo.

## Cómo presentar

1. Abrir `index.html` en cualquier navegador (Chrome/Edge/Firefox). Doble clic basta.
2. Navegar con **→ / ←** (o barra espaciadora). `Esc` muestra la vista general de todas las slides.
3. Tecla **S** abre la **vista de presentador** (notas + cronómetro + siguiente slide).
4. **F** activa pantalla completa para proyectar.

> La presentación funciona **sin internet**, salvo la slide 15 (demo): el `iframe` carga el Swagger real de Railway, que sí requiere conexión.

## Antes de la defensa (checklist)

- [ ] Probar `index.html` en el PC/navegador que se usará para proyectar.
- [ ] Verificar que la API esté **Online**: abrir `https://telco-api-production-e466.up.railway.app/health` → debe decir `"status":"healthy"`.
- [ ] Mantener **Supabase activo** (entrar al dashboard el día previo; el plan free pausa por inactividad).
- [ ] Tener abierto en otra pestaña el Swagger por si el `iframe` falla en la sala.

## Respaldo

- `Presentacion_Defensa_Evaluacion2.pdf` — versión PDF de las 17 slides (por si no se puede usar el navegador o lo piden subir).

## Estructura (17 slides · ~15 min)

| # | Slide | Quién |
|---|---|---|
| 1 | Portada (integrantes + roles + sección) | Ambos |
| 2 | Agenda | Ambos |
| 3 | El problema / necesidad | Benjamín |
| 4 | DataOps vs tradicional | Benjamín |
| 5 | Arquitectura cloud desacoplada | Diego |
| 6 | Pipeline 4 etapas (ciclo de vida) | Ambos |
| 7 | Metodología PMBOK híbrida | Diego |
| 8 | Planificación (WBS + Gantt + fechas) | Diego |
| 9–12 | Etapas 1–4 del pipeline | B / D / B / D |
| 13 | Plan de seguridad | Diego |
| 14 | KPIs de monitoreo | Diego |
| 15 | **Demo funcional en vivo** | Ambos |
| 16 | Conclusiones y próximos pasos | Ambos |
| 17 | Cierre / preguntas | Ambos |

El guion detallado de qué decir en cada slide está en [`../presentacion.md`](../presentacion.md).
