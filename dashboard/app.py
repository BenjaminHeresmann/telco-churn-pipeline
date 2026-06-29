"""Dashboard BI — Panel de Riesgo de Abandono (Telco Churn).

Evaluacion 3, ITY1101. Se conecta a la tabla `predicciones` de Supabase
(resultado del modelo) y la cruza con `clientes` y `carga_logs` del pipeline.
Si la BD no esta disponible, cae a los artefactos locales de outputs/modelo/.

Ejecutar:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "modelo"
load_dotenv(ROOT / ".env")

AZUL = "#1e3a8a"
ROJO = "#ef4444"
VERDE = "#22c55e"

st.set_page_config(page_title="Telco Churn — Panel de Riesgo", page_icon="📉", layout="wide")


# ----------------------------------------------------------------- conexion
def _engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(url, future=True, pool_pre_ping=True,
                         connect_args={"connect_timeout": 8})


# Microservicios del modelo (para la demo en vivo). Por defecto, los desplegados.
TRAINER_URL = os.getenv("TRAINER_URL", "https://telco-trainer-production.up.railway.app")
PREDICTOR_URL = os.getenv("PREDICTOR_URL", "https://telco-predictor-production.up.railway.app")


def _post(url: str, timeout: int = 120) -> dict:
    """POST sin cuerpo a un microservicio del modelo y devuelve el JSON."""
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _vaciar_predicciones() -> None:
    """Vacía la tabla `predicciones` (para arrancar la demo desde cero)."""
    eng = _engine()
    if eng is not None:
        with eng.begin() as c:
            c.execute(text("TRUNCATE TABLE predicciones"))


@st.cache_data(ttl=300, show_spinner="Cargando datos desde Supabase…")
def cargar():
    """Devuelve (predicciones+segmento, carga_logs, n_rechazados, origen)."""
    try:
        eng = _engine()
        if eng is None:
            raise RuntimeError("sin DATABASE_URL")
        q = """
            SELECT p.customer_id, p.churn_real, p.churn_pred, p.churn_proba,
                   p.acierto, p.modelo,
                   c.contract, c.tenure, c.monthly_charges, c.internet_service,
                   c.payment_method, c.senior_citizen, c.tenure_group
            FROM predicciones p
            LEFT JOIN clientes c ON p.customer_id = c.customer_id
        """
        pred = pd.read_sql(q, eng)
        logs = pd.read_sql("SELECT * FROM carga_logs ORDER BY fecha_ejecucion DESC LIMIT 1", eng)
        with eng.connect() as cn:
            n_rech = cn.execute(text("SELECT COUNT(*) FROM clientes_rechazados")).scalar()
            r = cn.execute(text("SELECT metricas FROM modelo_artefacto ORDER BY fecha DESC LIMIT 1")).scalar()
        met_modelo = (r if isinstance(r, dict) else json.loads(r)) if r else None
        return pred, logs, n_rech, "Supabase (en vivo)", met_modelo
    except Exception as exc:  # fallback local
        pred = pd.read_csv(OUT / "predicciones_test.csv")
        for col in ["contract", "tenure", "monthly_charges", "internet_service",
                    "payment_method", "senior_citizen", "tenure_group"]:
            if col not in pred.columns:
                pred[col] = None
        return pred, pd.DataFrame(), None, f"CSV local (sin BD: {str(exc)[:40]})", None


def metricas(pred: pd.DataFrame) -> dict:
    tp = int(((pred.churn_real == 1) & (pred.churn_pred == 1)).sum())
    tn = int(((pred.churn_real == 0) & (pred.churn_pred == 0)).sum())
    fp = int(((pred.churn_real == 0) & (pred.churn_pred == 1)).sum())
    fn = int(((pred.churn_real == 1) & (pred.churn_pred == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else 0
    pre = tp / (tp + fp) if tp + fp else 0
    acc = (tp + tn) / len(pred) if len(pred) else 0
    f1 = 2 * pre * rec / (pre + rec) if pre + rec else 0
    return dict(TP=tp, TN=tn, FP=fp, FN=fn, recall=rec, precision=pre, accuracy=acc, f1=f1)


# --------------------------------------------------------------------- datos
pred, logs, n_rech, origen, met_modelo = cargar()
# Métricas HONESTAS desde el registro del modelo (holdout); si no hay, se calculan.
m = {**metricas(pred), **(met_modelo or {})}
n_eval = int(met_modelo["n_test"]) if met_modelo and met_modelo.get("n_test") else len(pred)

# ------------------------------------------------------------------ cabecera
st.title("📉 Panel de Riesgo de Abandono — Telco Churn")
modelo = pred["modelo"].iloc[0] if "modelo" in pred.columns and len(pred) else "—"
st.caption(f"Modelo en producción: **{modelo}**  ·  Fuente: {origen}  ·  "
           f"Métricas sobre conjunto de prueba (holdout, {n_eval:,}) · "
           f"scoring de riesgo sobre {len(pred):,} clientes")

# ------------------------------------------------- panel de demo en vivo
with st.container():
    b1, b2, b3 = st.columns([1.3, 1.3, 1.4])
    if b1.button("🔧 1. Entrenar modelo", use_container_width=True,
                 help="Llama al microservicio trainer (POST /train)"):
        with st.spinner("Entrenando el modelo en la nube…"):
            try:
                res = _post(f"{TRAINER_URL}/train", timeout=120)
                rec = res.get("metricas_holdout", {}).get("recall", 0) * 100
                st.cache_data.clear()
                st.success(f"✅ Modelo entrenado y guardado en Supabase · recall {rec:.1f}%. "
                           f"Ahora pulsa **▶ Ejecutar predicción**.")
            except Exception as e:
                st.error(f"No se pudo entrenar: {e}")
    if b2.button("▶ 2. Ejecutar predicción", type="primary", use_container_width=True,
                 help="Llama al microservicio predictor (POST /predict/batch)"):
        with st.spinner("Puntuando a los clientes en vivo…"):
            try:
                try:
                    _post(f"{PREDICTOR_URL}/reload", timeout=60)  # usar el modelo más reciente
                except Exception:
                    pass
                res = _post(f"{PREDICTOR_URL}/predict/batch", timeout=120)
                st.cache_data.clear()
                st.toast(f"✅ {res.get('clientes_puntuados', 0):,} clientes puntuados · "
                         f"{res.get('en_riesgo', 0):,} en riesgo", icon="🎯")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo predecir: {e}")
    with b3.expander("⚙️ Preparar demo (vaciar)"):
        if st.button("🧹 Vaciar predicciones para empezar de cero"):
            _vaciar_predicciones()
            st.cache_data.clear()
            st.rerun()

if len(pred) == 0:
    st.warning("📭 **El panel está esperando una predicción.** Pulsa **▶ Ejecutar predicción** "
               "para puntuar a los clientes en vivo y ver el dashboard llenarse.")

# Gini: del modelo en producción (holdout); si no, de la comparativa
gini = m.get("gini")
try:
    comp = pd.read_csv(OUT / "metricas_modelos.csv")
    if gini is None:
        fila = comp.loc[comp.modelo == modelo]
        gini = float(fila.gini.iloc[0]) if len(fila) else None
except Exception:
    comp = pd.DataFrame()

# --------------------------------------------------------------------- KPIs
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Recall (prioritaria)", f"{m['recall']*100:.1f}%", help="De los que se van, cuántos detectamos. Es la métrica clave en retención.")
c2.metric("F1-score", f"{m['f1']:.3f}")
c3.metric("Precision", f"{m['precision']*100:.1f}%")
c4.metric("Accuracy", f"{m['accuracy']*100:.1f}%", help="Engañosa con desbalance: 'todo No-churn' daría ~73,5%.")
c5.metric("Gini", f"{gini:.3f}" if gini is not None else "—")
c6.metric("Clientes en riesgo", f"{int((pred.churn_pred==1).sum()):,}", help="Predichos como churn → foco de retención.")

st.divider()

# ------------------------------------------------- fila 1: confusión + drivers
col_a, col_b = st.columns([1, 1.2])

with col_a:
    st.subheader("Matriz de confusión")
    cm = [[m["TN"], m["FP"]], [m["FN"], m["TP"]]]
    fig = px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                    x=["Pred: No churn", "Pred: Churn"],
                    y=["Real: No churn", "Real: Churn"], aspect="auto")
    fig.update_layout(height=360, coloraxis_showscale=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Sobre el conjunto de prueba (holdout). 🔴 **{m['FN']} Falsos Negativos** = "
               f"clientes que se van y NO detectamos (el error más caro). ✅ {m['TP']} detectados.")

with col_b:
    st.subheader("Top variables que predicen el abandono")
    try:
        imp = pd.read_csv(OUT / "importancia_variables.csv", index_col=0).head(10)
        imp.index = [i.split("__", 1)[-1] for i in imp.index]
        fig = px.bar(imp.iloc[::-1], x="peso", orientation="h", color_discrete_sequence=[AZUL])
        fig.update_layout(height=360, showlegend=False, yaxis_title="", xaxis_title="peso",
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info(f"Sin importancia de variables ({e})")

# ------------------------------------------------- fila 2: segmentos + modelos
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Tasa de churn real por segmento")
    seg = st.selectbox("Segmento", ["contract", "internet_service", "payment_method", "tenure_group"],
                       format_func=lambda s: {"contract": "Tipo de contrato",
                                              "internet_service": "Servicio de internet",
                                              "payment_method": "Método de pago",
                                              "tenure_group": "Antigüedad (meses)"}[s])
    if seg in pred.columns and pred[seg].notna().any():
        g = pred.groupby(seg)["churn_real"].mean().mul(100).round(1).sort_values(ascending=False)
        fig = px.bar(g, color_discrete_sequence=[ROJO])
        fig.update_layout(height=320, showlegend=False, yaxis_title="% churn", xaxis_title="",
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Segmento no disponible en este origen de datos.")

with col_d:
    st.subheader("Comparativa de modelos (test)")
    if len(comp):
        cc = comp.set_index("modelo")[["recall", "f1", "accuracy"]].mul(1)
        fig = px.bar(cc, barmode="group",
                     color_discrete_sequence=[ROJO, AZUL, "#94a3b8"])
        fig.update_layout(height=320, yaxis_title="", xaxis_title="",
                          legend_title="", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("La balanceada sacrifica accuracy para **subir recall** (detectar más abandonos).")
    else:
        st.info("Sin comparativa de modelos.")

st.divider()

# ------------------------------------------------- fila 3: tabla filtrable errores
st.subheader("🔎 Análisis de errores caso a caso")
pred = pred.copy()
pred["tipo"] = "Acierto"
pred.loc[(pred.churn_real == 1) & (pred.churn_pred == 0), "tipo"] = "Falso Negativo (se fue, no detectado)"
pred.loc[(pred.churn_real == 0) & (pred.churn_pred == 1), "tipo"] = "Falso Positivo (falsa alarma)"

f1c, f2c, f3c = st.columns([1.4, 1, 1])
tipos = f1c.multiselect("Tipo de caso", sorted(pred.tipo.unique()),
                        default=[t for t in pred.tipo.unique() if "Falso" in t])
contratos = f2c.multiselect("Contrato", sorted(pred.contract.dropna().unique()) if "contract" in pred else [])
prob_min = f3c.slider("Probabilidad de churn ≥", 0.0, 1.0, 0.0, 0.05)

vis = pred[pred.tipo.isin(tipos)] if tipos else pred
if contratos:
    vis = vis[vis.contract.isin(contratos)]
vis = vis[vis.churn_proba >= prob_min]

cols_tabla = [c for c in ["customer_id", "tipo", "churn_proba", "contract", "tenure",
                          "monthly_charges", "internet_service", "payment_method"] if c in vis.columns]
st.caption(f"Mostrando **{len(vis):,}** de {len(pred):,} casos.")
st.dataframe(vis[cols_tabla].sort_values("churn_proba", ascending=False),
             use_container_width=True, height=320, hide_index=True)

# ------------------------------------------------- fila 4: volumen del pipeline
st.divider()
st.subheader("🔧 Volumen por etapa del pipeline DataOps")
if len(logs):
    r = logs.iloc[0]
    leidos = int(r["registros_leidos"]); insertados = int(r["registros_insertados"])
    rech = int(n_rech) if n_rech is not None else int(r.get("registros_rechazados", 0))
    fig = go.Figure(go.Funnel(
        y=["Ingesta (leídos)", "Validados/insertados", "Rechazados (auditoría)"],
        x=[leidos, insertados, rech],
        textinfo="value+percent initial",
        marker=dict(color=[AZUL, VERDE, ROJO])))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Última corrida del pipeline: {leidos:,} leídos → {insertados:,} cargados "
               f"a Supabase · estado **{r['estado']}** · {r['duracion_segundos']}s.")
else:
    st.info("Logs del pipeline no disponibles (BD dormida o sin corridas).")
