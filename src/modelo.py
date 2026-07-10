"""Etapa de modelado (Evaluacion 3): entrenamiento, evaluacion e INFERENCIA del modelo de churn.

Construye SOBRE el pipeline DataOps de Eval 2: toma los datos ya limpios y
validados (tabla `clientes` de Supabase o el ultimo CSV validado) y trabaja en
tres modos, separando entrenamiento de prediccion (ciclo train/inference):

    python src/modelo.py --eval                 # entrena y COMPARA 4 modelos + graficos (informe)
    python src/modelo.py --train                # entrena el modelo final y lo GUARDA en Supabase
    python src/modelo.py --predict              # CARGA el modelo guardado y predice (sin re-entrenar)

Modos --train / --predict habilitan el despliegue como microservicios separados
(un contenedor entrena, otro predice), compartiendo el modelo entrenado via
Supabase (tabla `modelo_artefacto`) — igual que las capas del pipeline comparten
datos via Supabase. Ver src/serve_modelo.py (capa FastAPI de serving).

Decisiones de diseno:
- Variable objetivo: `churn` (booleana). Problema: clasificacion binaria.
- Metrica prioritaria: RECALL (el Falso Negativo es el error mas caro en retencion).
- Desbalance (26,5%): se trata con `class_weight='balanced'`.
- Modelo de produccion: Regresion Logistica balanceada (mejor F1/recall, interpretable).
"""
from __future__ import annotations

import argparse
import base64
import glob
import io
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from utils.logger import get_logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_VALIDATED = PROJECT_ROOT / "data" / "validated"
OUT_DIR = PROJECT_ROOT / "outputs" / "modelo"
RANDOM_STATE = 42
MODELO_NOMBRE = "LogReg balanceada"

log = get_logger("modelo")

# Columnas que NO entran como predictoras
DROP_COLS = ["customerID", "Churn", "tenure_group"]
NUM_CONTINUAS = ["tenure", "MonthlyCharges", "TotalCharges"]


# --------------------------------------------------------------------- carga
def cargar_datos(fuente: str = "csv") -> pd.DataFrame:
    """Carga el dataset limpio+validado desde el CSV validado o desde Supabase."""
    if fuente == "supabase":
        from carga_bd import MAPEO_COLUMNAS, _build_engine

        log.info("Cargando datos desde Supabase (tabla clientes)")
        engine = _build_engine()
        df = pd.read_sql("SELECT * FROM clientes", engine)
        inverso = {v: k for k, v in MAPEO_COLUMNAS.items()}  # snake_case -> esquema CSV
        df = df.rename(columns=inverso)
        if "fecha_ingesta" in df.columns:
            df = df.drop(columns=["fecha_ingesta"])
    else:
        archivos = sorted(DATA_VALIDATED.glob("telco_churn_valid_*.csv"))
        if not archivos:
            raise FileNotFoundError(f"No hay CSV validado en {DATA_VALIDATED}")
        ruta = archivos[-1]
        log.info("Cargando datos desde %s", ruta.name)
        df = pd.read_csv(ruta)

    if "Churn" in df.columns:
        df["Churn"] = df["Churn"].astype(int)
    return df


def _features(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve la matriz de predictoras X (sin id, target ni columnas redundantes)."""
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns]).copy()
    bool_cols = X.select_dtypes(include="bool").columns
    X[bool_cols] = X[bool_cols].astype(int)
    return X


# ------------------------------------------------------------- preprocesador
def construir_preprocesador(X: pd.DataFrame) -> ColumnTransformer:
    """ColumnTransformer: escala continuas, deja binarias, one-hot a categoricas."""
    binarias = [c for c in X.columns if set(pd.unique(X[c])) <= {0, 1} and c not in NUM_CONTINUAS]
    categoricas = [c for c in X.columns if c not in NUM_CONTINUAS + binarias]
    return ColumnTransformer([
        ("num", StandardScaler(), NUM_CONTINUAS),
        ("bin", "passthrough", binarias),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categoricas),
    ])


def _modelo_produccion(X: pd.DataFrame) -> Pipeline:
    """Pipeline del modelo elegido (Regresion Logistica balanceada)."""
    return Pipeline([
        ("pre", construir_preprocesador(X)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE)),
    ])


def _metricas(y_true, y_pred, proba) -> dict:
    cm = confusion_matrix(y_true, y_pred)
    auc = roc_auc_score(y_true, proba)
    return {
        "modelo": MODELO_NOMBRE,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred), 4),
        "recall": round(recall_score(y_true, y_pred), 4),
        "f1": round(f1_score(y_true, y_pred), 4),
        "roc_auc": round(auc, 4),
        "gini": round(2 * auc - 1, 4),
        "TN": int(cm[0, 0]), "FP": int(cm[0, 1]), "FN": int(cm[1, 0]), "TP": int(cm[1, 1]),
        "n_test": int(len(y_true)),
    }


# ------------------------------------------------------- entrenamiento (prod)
def entrenar_modelo(df: pd.DataFrame) -> tuple[Pipeline, dict]:
    """Entrena el modelo de produccion. Evalua en un holdout (70/30 estratificado)
    para reportar metricas honestas y luego RE-AJUSTA con TODOS los datos
    etiquetados (mejor modelo final). Devuelve (pipeline_final, metricas)."""
    X = _features(df)
    y = df["Churn"]
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.30, stratify=y, random_state=RANDOM_STATE)

    evaluador = _modelo_produccion(X).fit(X_tr, y_tr)
    met = _metricas(y_te, evaluador.predict(X_te), evaluador.predict_proba(X_te)[:, 1])
    log.info("Holdout | recall=%.3f f1=%.3f gini=%.3f", met["recall"], met["f1"], met["gini"])

    final = _modelo_produccion(X).fit(X, y)  # modelo final con todo el dato etiquetado
    log.info("Modelo final entrenado sobre %d registros", len(X))
    return final, met


# ------------------------------------------------ persistencia del modelo (BD)
def _tabla_artefacto(engine) -> None:
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS modelo_artefacto (
                id          SERIAL PRIMARY KEY,
                nombre      VARCHAR(60) NOT NULL,
                artefacto   TEXT        NOT NULL,           -- modelo serializado (joblib + base64)
                metricas    JSONB,
                fecha       TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            ALTER TABLE modelo_artefacto ENABLE ROW LEVEL SECURITY;
        """))


def guardar_modelo_supabase(pipe: Pipeline, met: dict, engine=None) -> None:
    """Serializa el modelo (joblib->base64) y lo guarda en Supabase. Mantiene 1 vigente."""
    from sqlalchemy import text
    if engine is None:
        from carga_bd import _build_engine
        engine = _build_engine()
    _tabla_artefacto(engine)
    buf = io.BytesIO()
    joblib.dump(pipe, buf)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE modelo_artefacto RESTART IDENTITY"))
        conn.execute(
            text("INSERT INTO modelo_artefacto (nombre, artefacto, metricas) "
                 "VALUES (:n, :a, CAST(:m AS JSONB))"),
            {"n": MODELO_NOMBRE, "a": b64, "m": json.dumps(met)},
        )
    log.info("Modelo guardado en Supabase (modelo_artefacto) | %d KB", len(b64) // 1024)


def cargar_modelo_supabase(engine=None) -> tuple[Pipeline, dict]:
    """Carga el modelo entrenado mas reciente desde Supabase. NO re-entrena."""
    from sqlalchemy import text
    if engine is None:
        from carga_bd import _build_engine
        engine = _build_engine()
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT artefacto, metricas FROM modelo_artefacto ORDER BY fecha DESC LIMIT 1"
        )).fetchone()
    if not row:
        raise RuntimeError("No hay modelo entrenado en Supabase. Ejecuta primero --train.")
    pipe = joblib.load(io.BytesIO(base64.b64decode(row[0])))
    met = row[1] if isinstance(row[1], dict) else json.loads(row[1])
    log.info("Modelo cargado desde Supabase (sin re-entrenar)")
    return pipe, met


# ---------------------------------------------------------------- prediccion
def predecir_df(pipe: Pipeline, df: pd.DataFrame) -> pd.DataFrame:
    """Predice churn sobre un conjunto de clientes usando el modelo YA entrenado."""
    X = _features(df)
    proba = pipe.predict_proba(X)[:, 1]
    pred = pipe.predict(X)
    out = pd.DataFrame({
        "customer_id": df["customerID"].values if "customerID" in df.columns else range(len(df)),
        "churn_pred": pred.astype(int),
        "churn_proba": np.round(proba, 4),
        "modelo": MODELO_NOMBRE,
    })
    if "Churn" in df.columns:  # si hay etiqueta real, calcula acierto
        out["churn_real"] = df["Churn"].astype(int).values
        out["acierto"] = (out["churn_pred"] == out["churn_real"])
    return out


def predecir_cliente(pipe: Pipeline, customer_id: str, engine) -> dict:
    """Predice el churn de UN cliente existente (lo busca en `clientes` por id)."""
    from carga_bd import MAPEO_COLUMNAS
    from sqlalchemy import text
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM clientes WHERE customer_id = :id"),
                           {"id": customer_id}).mappings().fetchone()
    if not row:
        raise KeyError(customer_id)
    df = pd.DataFrame([dict(row)]).rename(columns={v: k for k, v in MAPEO_COLUMNAS.items()})
    if "fecha_ingesta" in df.columns:
        df = df.drop(columns=["fecha_ingesta"])
    pr = predecir_df(pipe, df).iloc[0]
    return {
        "customer_id": customer_id,
        "churn_predicho": bool(pr["churn_pred"]),
        "probabilidad_churn": float(pr["churn_proba"]),
        "modelo": MODELO_NOMBRE,
    }


# ------------------------------------- prediccion de un cliente NUEVO (demo en vivo)
# Plantilla con los 19 predictores (nombres de esquema CSV) y defaults reales del
# dataset (modas categoricas / medianas numericas). Lo que el usuario no especifique
# se completa con estos valores; TotalCharges se autocalcula si no se entrega.
CLIENTE_TEMPLATE = {
    "gender": "Male", "SeniorCitizen": 0, "Partner": False, "Dependents": False,
    "tenure": 29, "PhoneService": True, "MultipleLines": "No",
    "InternetService": "Fiber optic", "OnlineSecurity": "No", "OnlineBackup": "No",
    "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "No",
    "StreamingMovies": "No", "Contract": "Month-to-month", "PaperlessBilling": True,
    "PaymentMethod": "Electronic check", "MonthlyCharges": 70.35, "TotalCharges": None,
}
_BIN_COLS = ["SeniorCitizen", "Partner", "Dependents", "PhoneService", "PaperlessBilling"]

# Traducciones para la explicabilidad (nombre tecnico del modelo -> español legible)
_COL_ES = {
    "tenure": "Antigüedad", "MonthlyCharges": "Cargo mensual", "TotalCharges": "Cargo total",
    "Contract": "Contrato", "InternetService": "Servicio de internet",
    "PaymentMethod": "Método de pago", "TechSupport": "Soporte técnico",
    "OnlineSecurity": "Seguridad online", "OnlineBackup": "Respaldo online",
    "DeviceProtection": "Protección de dispositivo", "StreamingTV": "Streaming TV",
    "StreamingMovies": "Streaming películas", "MultipleLines": "Líneas múltiples",
    "PhoneService": "Servicio telefónico", "PaperlessBilling": "Factura electrónica",
    "Partner": "Pareja", "Dependents": "Dependientes", "SeniorCitizen": "Adulto mayor",
    "gender": "Género",
}
_VAL_ES = {
    "Month-to-month": "Mes a mes", "One year": "Un año", "Two year": "Dos años",
    "Fiber optic": "Fibra óptica", "DSL": "DSL", "No": "No", "Yes": "Sí",
    "Electronic check": "Cheque electrónico", "Mailed check": "Cheque por correo",
    "Bank transfer (automatic)": "Transferencia bancaria",
    "Credit card (automatic)": "Tarjeta de crédito", "No internet service": "Sin internet",
    "No phone service": "Sin teléfono", "Male": "Masculino", "Female": "Femenino",
}


def _to01(v) -> int:
    """Normaliza un valor binario (bool / int / 'Yes'/'No') a 0/1."""
    if isinstance(v, str):
        return 1 if v.strip().lower() in ("yes", "sí", "si", "true", "1") else 0
    return int(bool(v))


def _fila_cliente(datos: dict) -> pd.DataFrame:
    """Arma la fila (1x19) del cliente: plantilla + overrides del usuario."""
    c = {**CLIENTE_TEMPLATE, **{k: v for k, v in (datos or {}).items()
                                if k in CLIENTE_TEMPLATE and v is not None}}
    for b in _BIN_COLS:
        c[b] = _to01(c[b])
    if c.get("TotalCharges") is None:  # cargo total ~ antiguedad * cargo mensual
        c["TotalCharges"] = round(float(c["tenure"]) * float(c["MonthlyCharges"]), 2)
    return pd.DataFrame([c])


def _nombre_factor(nombre: str, fila: dict) -> str:
    """Traduce un nombre tecnico del modelo a texto legible.
    'cat__Contract_Month-to-month' -> 'Contrato: Mes a mes'."""
    tipo, resto = nombre.split("__", 1)
    if tipo == "cat":
        col, _, val = resto.partition("_")
        return f"{_COL_ES.get(col, col)}: {_VAL_ES.get(val, val)}"
    if tipo == "num":
        v = fila.get(resto)
        unidad = " meses" if resto == "tenure" else ""
        return f"{_COL_ES.get(resto, resto)} = {v:g}{unidad}" if v is not None else _COL_ES.get(resto, resto)
    return f"{_COL_ES.get(resto, resto)}: {'Sí' if fila.get(resto) else 'No'}"  # binaria


def explicar_prediccion(pipe: Pipeline, X: pd.DataFrame, top: int = 4) -> dict:
    """Descompone la prediccion de la Regresion Logistica: la contribucion de cada
    variable al log-odds es coef * valor_transformado. Devuelve los factores que mas
    empujan a la fuga (contrib>0) y los que retienen (contrib<0). Interpretabilidad
    real del modelo (no inventada), sin dependencias nuevas."""
    pre, clf = pipe.named_steps["pre"], pipe.named_steps["clf"]
    if not hasattr(clf, "coef_"):
        return {"empujan_a_fuga": [], "retienen": []}
    z = np.asarray(pre.transform(X))[0]
    nombres = pre.get_feature_names_out()
    contrib = clf.coef_[0] * z
    f0 = X.iloc[0].to_dict()
    orden = np.argsort(contrib)
    fuga = [{"factor": _nombre_factor(nombres[i], f0), "peso": round(float(contrib[i]), 3)}
            for i in orden[::-1] if contrib[i] > 1e-6][:top]
    ret = [{"factor": _nombre_factor(nombres[i], f0), "peso": round(float(contrib[i]), 3)}
           for i in orden if contrib[i] < -1e-6][:2]
    return {"empujan_a_fuga": fuga, "retienen": ret}


def predecir_cliente_nuevo(pipe: Pipeline, datos: dict) -> dict:
    """Predice el churn de un cliente NUEVO (no existe en la base). Sin reentrenar ni
    persistir: prediccion efimera para el demo en vivo sobre datos que el modelo no vio."""
    X = _features(_fila_cliente(datos))
    proba = float(pipe.predict_proba(X)[:, 1][0])
    nivel = "alto" if proba >= 0.5 else "medio" if proba >= 0.3 else "bajo"
    return {
        "probabilidad_churn": round(proba, 4),
        "churn_predicho": proba >= 0.5,
        "nivel_riesgo": nivel,
        "factores": explicar_prediccion(pipe, X),
        "modelo": MODELO_NOMBRE,
        "nota": "Cliente no presente en la base — predicción sobre datos no vistos.",
    }


def persistir_predicciones(predicciones: pd.DataFrame, engine=None) -> int:
    """Refresca la tabla `predicciones` en Supabase (fuente del dashboard BI)."""
    from sqlalchemy import text
    if engine is None:
        from carga_bd import _build_engine
        engine = _build_engine()
    cols = ["customer_id", "churn_real", "churn_pred", "churn_proba", "acierto", "modelo"]
    df = predicciones.reindex(columns=[c for c in cols if c in predicciones.columns or c in
                                       ("churn_real", "acierto")])
    for c in ("churn_real", "acierto"):
        if c not in df.columns:
            df[c] = None
    ddl = text("""
        CREATE TABLE IF NOT EXISTS predicciones (
            customer_id VARCHAR(20), churn_real SMALLINT, churn_pred SMALLINT,
            churn_proba NUMERIC(6,4), acierto BOOLEAN, modelo VARCHAR(40),
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);
        ALTER TABLE predicciones ENABLE ROW LEVEL SECURITY;
    """)
    with engine.begin() as conn:
        conn.execute(ddl)
        conn.execute(text("TRUNCATE TABLE predicciones"))
    df[cols].to_sql("predicciones", engine, if_exists="append", index=False, method="multi")
    log.info("Persistidas %d predicciones en Supabase", len(df))
    return len(df)


# ============================================================ MODO --eval ===
# (comparativa de 4 modelos + graficos; alimenta el informe. Matplotlib se
#  importa de forma diferida para no exigirlo en la imagen de serving.)
def construir_modelos() -> dict:
    return {
        "LogReg (baseline)": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "Arbol (baseline)": DecisionTreeClassifier(max_depth=5, random_state=RANDOM_STATE),
        "LogReg balanceada": LogisticRegression(max_iter=1000, class_weight="balanced",
                                                random_state=RANDOM_STATE),
        "RandomForest balanceado": RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                                          random_state=RANDOM_STATE, n_jobs=-1),
    }


def analisis_exploratorio(df: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set_theme(style="whitegrid")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n, pos = len(df), int(df["Churn"].sum())
    df[NUM_CONTINUAS].describe().round(2).to_csv(OUT_DIR / "eda_descriptiva_numericas.csv")
    bivar = {}
    for col in ["Contract", "InternetService", "PaymentMethod", "tenure_group",
                "SeniorCitizen", "PaperlessBilling", "Dependents", "Partner"]:
        if col in df.columns:
            bivar[col] = df.groupby(col)["Churn"].agg(n="count",
                                                      churn_pct=lambda s: round(100 * s.mean(), 1))
    with open(OUT_DIR / "eda_bivariado_churn.txt", "w", encoding="utf-8") as f:
        for col, t in bivar.items():
            f.write(f"== {col} ==\n{t.to_string()}\n\n")
    plt.figure(figsize=(5, 4))
    sns.heatmap(df[NUM_CONTINUAS + ["Churn"]].corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0)
    plt.title("Matriz de correlacion (numericas + churn)")
    plt.tight_layout(); plt.savefig(OUT_DIR / "correlacion_numericas.png", dpi=130); plt.close()
    plt.figure(figsize=(4.5, 4))
    ax = sns.barplot(x=["No churn", "Churn"], y=[n - pos, pos], hue=["No churn", "Churn"],
                     palette=["#22c55e", "#ef4444"], legend=False)
    for i, v in enumerate([n - pos, pos]):
        ax.text(i, v + 40, f"{v}\n({100 * v / n:.1f}%)", ha="center", fontsize=9)
    plt.title("Distribucion de la clase (desbalance)"); plt.ylabel("clientes")
    plt.tight_layout(); plt.savefig(OUT_DIR / "distribucion_churn.png", dpi=130); plt.close()


def entrenar_y_evaluar(df: pd.DataFrame) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set_theme(style="whitegrid")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    y, ids = df["Churn"], df["customerID"]
    X = _features(df)
    X_tr, X_te, y_tr, y_te, _, id_te = train_test_split(
        X, y, ids, test_size=0.30, stratify=y, random_state=RANDOM_STATE)
    pre = construir_preprocesador(X)
    filas, roc_data, fitted = [], {}, {}
    for nombre, clf in construir_modelos().items():
        pipe = Pipeline([("pre", pre), ("clf", clf)]).fit(X_tr, y_tr)
        fitted[nombre] = pipe
        p_te, proba = pipe.predict(X_te), pipe.predict_proba(X_te)[:, 1]
        p_tr = pipe.predict(X_tr)
        auc = roc_auc_score(y_te, proba)
        roc_data[nombre] = (*roc_curve(y_te, proba)[:2], auc)
        cm = confusion_matrix(y_te, p_te)
        filas.append({"modelo": nombre, "accuracy": round(accuracy_score(y_te, p_te), 4),
                      "precision": round(precision_score(y_te, p_te), 4),
                      "recall": round(recall_score(y_te, p_te), 4),
                      "f1": round(f1_score(y_te, p_te), 4), "roc_auc": round(auc, 4),
                      "gini": round(2 * auc - 1, 4), "acc_train": round(accuracy_score(y_tr, p_tr), 4),
                      "recall_train": round(recall_score(y_tr, p_tr), 4),
                      "TN": int(cm[0, 0]), "FP": int(cm[0, 1]), "FN": int(cm[1, 0]), "TP": int(cm[1, 1])})
    tabla = pd.DataFrame(filas)
    tabla.to_csv(OUT_DIR / "metricas_modelos.csv", index=False)
    log.info("Comparativa de modelos:\n%s", tabla.to_string(index=False))
    mejor = tabla.sort_values("f1", ascending=False).iloc[0]["modelo"]
    best = fitted[mejor]
    pred_best, proba_best = best.predict(X_te), best.predict_proba(X_te)[:, 1]

    plt.figure(figsize=(6.5, 5.5))
    for nombre, (fpr, tpr, auc) in roc_data.items():
        plt.plot(fpr, tpr, label=f"{nombre} (AUC={auc:.3f})")
    plt.plot([0, 1], [0, 1], "k--", alpha=.4); plt.xlabel("FPR (1 - especificidad)")
    plt.ylabel("TPR (recall)"); plt.title("Curvas ROC — comparativa de modelos")
    plt.legend(loc="lower right", fontsize=8); plt.tight_layout()
    plt.savefig(OUT_DIR / "roc_comparativa.png", dpi=130); plt.close()
    cm = confusion_matrix(y_te, pred_best)
    plt.figure(figsize=(5, 4.2))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["No churn", "Churn"], yticklabels=["No churn", "Churn"])
    plt.xlabel("Prediccion"); plt.ylabel("Real"); plt.title(f"Matriz de confusion — {mejor}")
    plt.tight_layout(); plt.savefig(OUT_DIR / "matriz_confusion_mejor.png", dpi=130); plt.close()
    try:
        feat = best.named_steps["pre"].get_feature_names_out()
        clf = best.named_steps["clf"]
        imp = (pd.Series(clf.feature_importances_, index=feat) if hasattr(clf, "feature_importances_")
               else pd.Series(np.abs(clf.coef_[0]), index=feat)).sort_values(ascending=False).head(15)
        plt.figure(figsize=(7.5, 5.5))
        sns.barplot(x=imp.values, y=[s.split("__", 1)[-1] for s in imp.index], color="#2563eb")
        plt.title(f"Top 15 variables — {mejor}"); plt.xlabel("peso"); plt.tight_layout()
        plt.savefig(OUT_DIR / "importancia_variables.png", dpi=130); plt.close()
        imp.rename("peso").to_csv(OUT_DIR / "importancia_variables.csv")
    except Exception as exc:  # pragma: no cover
        log.warning("No se pudo graficar importancia: %s", exc)
    predicciones = pd.DataFrame({
        "customer_id": id_te.values, "churn_real": y_te.values.astype(int),
        "churn_pred": pred_best.astype(int), "churn_proba": np.round(proba_best, 4),
        "acierto": (pred_best == y_te.values), "modelo": mejor})
    predicciones.to_csv(OUT_DIR / "predicciones_test.csv", index=False)
    with open(OUT_DIR / "resumen_modelo.json", "w", encoding="utf-8") as f:
        json.dump({"n_total": len(df), "churn_pct": round(100 * y.mean(), 2),
                   "mejor_modelo_por_f1": mejor, "metricas": tabla.to_dict(orient="records")},
                  f, ensure_ascii=False, indent=2)
    return {"tabla": tabla, "mejor": mejor, "predicciones": predicciones}


# --------------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser(description="Modelo de churn — entrenamiento, evaluacion e inferencia")
    parser.add_argument("--fuente", choices=["csv", "supabase"], default="csv")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--eval", action="store_true", help="Compara 4 modelos + graficos (informe)")
    modo.add_argument("--train", action="store_true", help="Entrena el modelo final y lo guarda en Supabase")
    modo.add_argument("--predict", action="store_true", help="Carga el modelo guardado y predice (sin re-entrenar)")
    parser.add_argument("--persistir", action="store_true", help="(con --eval) sube las predicciones a Supabase")
    args = parser.parse_args()

    df = cargar_datos(args.fuente)

    if args.train:
        pipe, met = entrenar_modelo(df)
        guardar_modelo_supabase(pipe, met)
        log.info("ENTRENAMIENTO OK | %s", met)
    elif args.predict:
        pipe, _ = cargar_modelo_supabase()
        pred = predecir_df(pipe, df)
        n = persistir_predicciones(pred)
        log.info("PREDICCION OK | %d clientes puntuados (sin re-entrenar)", n)
    else:  # --eval (por defecto)
        analisis_exploratorio(df)
        res = entrenar_y_evaluar(df)
        if args.persistir:
            persistir_predicciones(res["predicciones"])
        log.info("EVALUACION OK. Artefactos en %s", OUT_DIR.relative_to(PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover
        log.error("Fallo en modelado: %s", exc, exc_info=True)
        sys.exit(1)
