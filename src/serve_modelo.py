"""Capa de serving del modelo de churn (Evaluacion 3) — microservicios separados.

UN solo archivo / UNA sola imagen, cuyo ROL se define por la variable de entorno
`ROL` (igual que el patron "mismo contenedor, distinto comando por capa" de Eval 2):

    ROL=trainer    -> expone POST /train     (entrena y guarda el modelo en Supabase)
    ROL=predictor  -> expone /metrics, /predict/...  (carga el modelo y predice)

Los dos servicios se comunican SOLO via Supabase (tabla `modelo_artefacto`): el
trainer guarda el modelo entrenado, el predictor lo carga. No comparten disco
ni codigo en ejecucion — son contenedores/despliegues independientes.

Arranque:  uvicorn serve_modelo:app --app-dir src --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import modelo
from carga_bd import _build_engine

ROL = os.getenv("ROL", "predictor").strip().lower()


class ClienteNuevo(BaseModel):
    """Cliente inventado para el demo en vivo. Todos los campos son opcionales: lo que
    no se envie se completa con una plantilla de defaults reales del dataset."""
    gender: Optional[str] = None
    SeniorCitizen: Optional[int] = None
    Partner: Optional[bool] = None
    Dependents: Optional[bool] = None
    tenure: Optional[int] = None
    PhoneService: Optional[bool] = None
    MultipleLines: Optional[str] = None
    InternetService: Optional[str] = None
    OnlineSecurity: Optional[str] = None
    OnlineBackup: Optional[str] = None
    DeviceProtection: Optional[str] = None
    TechSupport: Optional[str] = None
    StreamingTV: Optional[str] = None
    StreamingMovies: Optional[str] = None
    Contract: Optional[str] = None
    PaperlessBilling: Optional[bool] = None
    PaymentMethod: Optional[str] = None
    MonthlyCharges: Optional[float] = None
    TotalCharges: Optional[float] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "Contract": "Month-to-month", "tenure": 2, "InternetService": "Fiber optic",
                "PaymentMethod": "Electronic check", "TechSupport": "No",
                "OnlineSecurity": "No", "MonthlyCharges": 95.0, "SeniorCitizen": 1,
                "PaperlessBilling": True, "Partner": False, "Dependents": False,
            }
        }
    }
app = FastAPI(
    title=f"Telco Churn — Modelo ({ROL})",
    description=("Microservicio de **entrenamiento**" if ROL == "trainer"
                 else "Microservicio de **inferencia** (predice con el modelo ya entrenado)"),
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def raiz():
    return {
        "servicio": "modelo-churn", "rol": ROL,
        "descripcion": ("Entrena el modelo y lo guarda en Supabase" if ROL == "trainer"
                        else "Carga el modelo desde Supabase y predice (sin re-entrenar)"),
        "endpoints": (["POST /train"] if ROL == "trainer"
                      else ["GET /metrics", "GET /predict/cliente/{customer_id}",
                            "POST /predict/batch", "POST /predict/nuevo"]),
    }


@app.get("/health")
def health():
    return {"estado": "ok", "rol": ROL}


# ============================================================ TRAINER ========
if ROL == "trainer":
    @app.post("/train")
    def train():
        """Entrena el modelo de churn sobre `clientes` y lo guarda en Supabase."""
        df = modelo.cargar_datos("supabase")
        pipe, met = modelo.entrenar_modelo(df)
        modelo.guardar_modelo_supabase(pipe, met)
        return {"estado": "entrenado", "modelo": modelo.MODELO_NOMBRE,
                "metricas_holdout": met,
                "mensaje": "Modelo guardado en Supabase (modelo_artefacto). El predictor ya puede usarlo."}


# ========================================================== PREDICTOR ========
else:
    _cache: dict = {}

    def _modelo():
        if "pipe" not in _cache:
            _cache["pipe"], _cache["met"] = modelo.cargar_modelo_supabase()
        return _cache["pipe"], _cache["met"]

    @app.get("/metrics")
    def metrics():
        """Metricas de evaluacion (holdout) del modelo en produccion."""
        try:
            _, met = _modelo()
            return {"modelo": modelo.MODELO_NOMBRE, "metricas_holdout": met}
        except Exception as exc:
            raise HTTPException(503, f"No hay modelo entrenado todavia: {exc}")

    @app.get("/predict/cliente/{customer_id}")
    def predict_cliente(customer_id: str):
        """Predice el riesgo de churn de UN cliente existente (sin re-entrenar)."""
        try:
            pipe, _ = _modelo()
            return modelo.predecir_cliente(pipe, customer_id, _build_engine())
        except KeyError:
            raise HTTPException(404, f"Cliente {customer_id} no encontrado en `clientes`")
        except Exception as exc:
            raise HTTPException(503, f"No se pudo predecir: {exc}")

    @app.post("/predict/batch")
    def predict_batch():
        """Puntua TODA la base de clientes con el modelo guardado y actualiza `predicciones`."""
        try:
            pipe, _ = _modelo()
            df = modelo.cargar_datos("supabase")
            pred = modelo.predecir_df(pipe, df)
            n = modelo.persistir_predicciones(pred)
            return {"estado": "ok", "clientes_puntuados": n,
                    "en_riesgo": int((pred["churn_pred"] == 1).sum()),
                    "mensaje": "Tabla `predicciones` actualizada (fuente del dashboard)."}
        except Exception as exc:
            raise HTTPException(503, f"No se pudo predecir en lote: {exc}")

    @app.post("/predict/nuevo")
    def predict_nuevo(cliente: ClienteNuevo):
        """Predice el riesgo de churn de un cliente NUEVO (inventado, que NO esta en la
        base y el modelo nunca vio). Reutiliza el pipeline entrenado (preprocesamiento +
        LogReg). Devuelve la probabilidad, el nivel de riesgo y los factores que explican
        la prediccion (interpretabilidad). No persiste nada: prediccion efimera de demo."""
        try:
            pipe, _ = _modelo()
            return modelo.predecir_cliente_nuevo(pipe, cliente.model_dump(exclude_none=True))
        except Exception as exc:
            raise HTTPException(503, f"No se pudo predecir el cliente nuevo: {exc}")

    @app.post("/reload")
    def reload_model():
        """Recarga el modelo desde Supabase (util tras un nuevo entrenamiento)."""
        _cache.clear()
        _modelo()
        return {"estado": "modelo recargado"}
