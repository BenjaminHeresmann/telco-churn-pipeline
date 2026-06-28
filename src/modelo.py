"""Etapa de modelado (Evaluacion 3): entrenamiento y evaluacion del modelo de churn.

Construye SOBRE el pipeline DataOps de Eval 2: toma los datos ya limpios y
validados (ultimo CSV validado, o la tabla `clientes` de Supabase) y entrena un
clasificador binario supervisado para predecir el abandono de clientes (`churn`).

Flujo (modulo 3.1 del ramo): diseno -> EDA/calidad -> preprocesamiento ->
split estratificado -> BASELINE (Regresion Logistica, Arbol) -> MEJORA
(Random Forest balanceado) -> metricas (matriz de confusion, accuracy,
precision, recall, F1, ROC-AUC, Gini) -> artefactos + predicciones persistibles.

Decisiones de diseno:
- Variable objetivo: `churn` (booleana). Problema: clasificacion binaria.
- Metrica prioritaria: RECALL. En retencion el costo del Falso Negativo
  (cliente que se va y NO detectamos) es mayor que el del Falso Positivo.
- Desbalance (26,5% churn): se trata con `class_weight='balanced'` (sin generar
  datos sinteticos). El accuracy es enganoso aqui (un modelo "todo No-churn"
  daria ~73,5%), por eso el foco esta en recall/F1.
- `tenure_group` se descarta (es una binarizacion de `tenure`, redundante).

Uso:
    python src/modelo.py                 # entrena desde el ultimo CSV validado
    python src/modelo.py --fuente supabase
    python src/modelo.py --persistir     # ademas sube las predicciones a Supabase
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
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

log = get_logger("modelo")
sns.set_theme(style="whitegrid")

# Columnas que NO entran como predictoras
DROP_COLS = ["customerID", "Churn", "tenure_group"]
NUM_CONTINUAS = ["tenure", "MonthlyCharges", "TotalCharges"]


# --------------------------------------------------------------------- carga
def cargar_datos(fuente: str = "csv") -> pd.DataFrame:
    """Carga el dataset limpio+validado desde el CSV validado o desde Supabase."""
    if fuente == "supabase":
        from carga_bd import _build_engine, MAPEO_COLUMNAS

        log.info("Cargando datos desde Supabase (tabla clientes)")
        engine = _build_engine()
        df = pd.read_sql("SELECT * FROM clientes", engine)
        # la BD usa snake_case; revertir al esquema del CSV para un flujo unico
        inverso = {v: k for k, v in MAPEO_COLUMNAS.items()}
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

    df["Churn"] = df["Churn"].astype(int)
    return df


# ----------------------------------------------------------------------- EDA
def analisis_exploratorio(df: pd.DataFrame) -> dict:
    """Estadistica descriptiva + analisis bivariado (tasa de churn por categoria)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n, pos = len(df), int(df["Churn"].sum())
    log.info("Dataset: %d filas | churn=%d (%.2f%%)", n, pos, 100 * pos / n)

    df[NUM_CONTINUAS].describe().round(2).to_csv(OUT_DIR / "eda_descriptiva_numericas.csv")

    bivar = {}
    for col in ["Contract", "InternetService", "PaymentMethod", "tenure_group",
                "SeniorCitizen", "PaperlessBilling", "Dependents", "Partner"]:
        if col not in df.columns:
            continue
        t = df.groupby(col)["Churn"].agg(n="count", churn_pct=lambda s: round(100 * s.mean(), 1))
        bivar[col] = t
    with open(OUT_DIR / "eda_bivariado_churn.txt", "w", encoding="utf-8") as f:
        for col, t in bivar.items():
            f.write(f"== {col} ==\n{t.to_string()}\n\n")

    # matriz de correlacion (numericas + target)
    plt.figure(figsize=(5, 4))
    sns.heatmap(df[NUM_CONTINUAS + ["Churn"]].corr(), annot=True, fmt=".2f",
                cmap="coolwarm", center=0)
    plt.title("Matriz de correlacion (numericas + churn)")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "correlacion_numericas.png", dpi=130)
    plt.close()

    # distribucion de clase (desbalance)
    plt.figure(figsize=(4.5, 4))
    ax = sns.barplot(x=["No churn", "Churn"], y=[n - pos, pos],
                     hue=["No churn", "Churn"], palette=["#22c55e", "#ef4444"], legend=False)
    for i, v in enumerate([n - pos, pos]):
        ax.text(i, v + 40, f"{v}\n({100 * v / n:.1f}%)", ha="center", fontsize=9)
    plt.title("Distribucion de la clase (desbalance)")
    plt.ylabel("clientes")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "distribucion_churn.png", dpi=130)
    plt.close()
    return {"n": n, "churn": pos, "churn_pct": round(100 * pos / n, 2)}


# ------------------------------------------------------------- preprocesador
def construir_preprocesador(X: pd.DataFrame) -> ColumnTransformer:
    """ColumnTransformer: escala continuas, deja binarias, one-hot a categoricas."""
    bool_cols = X.select_dtypes(include="bool").columns.tolist()
    binarias = ["SeniorCitizen"] + bool_cols
    categoricas = [c for c in X.columns if c not in NUM_CONTINUAS + binarias]
    return ColumnTransformer([
        ("num", StandardScaler(), NUM_CONTINUAS),
        ("bin", "passthrough", binarias),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categoricas),
    ])


def construir_modelos() -> dict:
    """Baseline (defaults del docente) + version balanceada + Random Forest.

    Nota: en scikit-learn la regularizacion L2 es el comportamiento por defecto
    de LogisticRegression (equivale al penalty='l2' que indica el material).
    """
    return {
        "LogReg (baseline)": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "Arbol (baseline)": DecisionTreeClassifier(max_depth=5, random_state=RANDOM_STATE),
        "LogReg balanceada": LogisticRegression(max_iter=1000, class_weight="balanced",
                                                random_state=RANDOM_STATE),
        "RandomForest balanceado": RandomForestClassifier(n_estimators=100,
                                                          class_weight="balanced",
                                                          random_state=RANDOM_STATE, n_jobs=-1),
    }


# ------------------------------------------------------------- entrenamiento
def entrenar_y_evaluar(df: pd.DataFrame) -> dict:
    """Entrena todos los modelos, calcula metricas y genera artefactos graficos."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    y = df["Churn"]
    ids = df["customerID"]
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns]).copy()
    X[X.select_dtypes(include="bool").columns] = X.select_dtypes(include="bool").astype(int)

    X_tr, X_te, y_tr, y_te, _, id_te = train_test_split(
        X, y, ids, test_size=0.30, stratify=y, random_state=RANDOM_STATE)
    log.info("Split 70/30 estratificado | train=%d (churn %.2f%%) test=%d (churn %.2f%%)",
             len(X_tr), 100 * y_tr.mean(), len(X_te), 100 * y_te.mean())

    pre = construir_preprocesador(X)
    filas, roc_data, fitted = [], {}, {}
    for nombre, clf in construir_modelos().items():
        pipe = Pipeline([("pre", pre), ("clf", clf)]).fit(X_tr, y_tr)
        fitted[nombre] = pipe
        p_te = pipe.predict(X_te)
        proba = pipe.predict_proba(X_te)[:, 1]
        p_tr = pipe.predict(X_tr)
        auc = roc_auc_score(y_te, proba)
        roc_data[nombre] = (*roc_curve(y_te, proba)[:2], auc)
        cm = confusion_matrix(y_te, p_te)
        filas.append({
            "modelo": nombre,
            "accuracy": round(accuracy_score(y_te, p_te), 4),
            "precision": round(precision_score(y_te, p_te), 4),
            "recall": round(recall_score(y_te, p_te), 4),
            "f1": round(f1_score(y_te, p_te), 4),
            "roc_auc": round(auc, 4),
            "gini": round(2 * auc - 1, 4),
            "acc_train": round(accuracy_score(y_tr, p_tr), 4),
            "recall_train": round(recall_score(y_tr, p_tr), 4),
            "TN": int(cm[0, 0]), "FP": int(cm[0, 1]),
            "FN": int(cm[1, 0]), "TP": int(cm[1, 1]),
        })

    tabla = pd.DataFrame(filas)
    tabla.to_csv(OUT_DIR / "metricas_modelos.csv", index=False)
    log.info("Comparativa de modelos:\n%s", tabla.to_string(index=False))

    mejor = tabla.sort_values("f1", ascending=False).iloc[0]["modelo"]
    best = fitted[mejor]
    pred_best = best.predict(X_te)
    proba_best = best.predict_proba(X_te)[:, 1]
    log.info("Mejor modelo por F1: %s", mejor)

    _graficar_roc(roc_data)
    _graficar_confusion(y_te, pred_best, mejor)
    _graficar_importancia(best, mejor)

    predicciones = pd.DataFrame({
        "customer_id": id_te.values,
        "churn_real": y_te.values.astype(int),
        "churn_pred": pred_best.astype(int),
        "churn_proba": np.round(proba_best, 4),
        "acierto": (pred_best == y_te.values),
        "modelo": mejor,
    })
    predicciones.to_csv(OUT_DIR / "predicciones_test.csv", index=False)

    resumen = {
        "n_total": len(df), "churn_pct": round(100 * y.mean(), 2),
        "split": "70/30 estratificado", "mejor_modelo_por_f1": mejor,
        "metricas": tabla.to_dict(orient="records"),
    }
    with open(OUT_DIR / "resumen_modelo.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    return {"tabla": tabla, "mejor": mejor, "predicciones": predicciones}


# ----------------------------------------------------------------- graficos
def _graficar_roc(roc_data: dict) -> None:
    plt.figure(figsize=(6.5, 5.5))
    for nombre, (fpr, tpr, auc) in roc_data.items():
        plt.plot(fpr, tpr, label=f"{nombre} (AUC={auc:.3f})")
    plt.plot([0, 1], [0, 1], "k--", alpha=.4)
    plt.xlabel("FPR (1 - especificidad)")
    plt.ylabel("TPR (recall)")
    plt.title("Curvas ROC — comparativa de modelos")
    plt.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "roc_comparativa.png", dpi=130)
    plt.close()


def _graficar_confusion(y_te, pred, nombre) -> None:
    cm = confusion_matrix(y_te, pred)
    plt.figure(figsize=(5, 4.2))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["No churn", "Churn"], yticklabels=["No churn", "Churn"])
    plt.xlabel("Prediccion")
    plt.ylabel("Real")
    plt.title(f"Matriz de confusion — {nombre}")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "matriz_confusion_mejor.png", dpi=130)
    plt.close()


def _graficar_importancia(pipe, nombre) -> None:
    try:
        feat = pipe.named_steps["pre"].get_feature_names_out()
        clf = pipe.named_steps["clf"]
        if hasattr(clf, "feature_importances_"):
            imp = pd.Series(clf.feature_importances_, index=feat)
            titulo = f"Top 15 variables (importancia) — {nombre}"
        else:
            imp = pd.Series(np.abs(clf.coef_[0]), index=feat)
            titulo = f"Top 15 variables (|coef|) — {nombre}"
        imp = imp.sort_values(ascending=False).head(15)
        plt.figure(figsize=(7.5, 5.5))
        sns.barplot(x=imp.values, y=[s.split("__", 1)[-1] for s in imp.index], color="#2563eb")
        plt.title(titulo)
        plt.xlabel("peso")
        plt.tight_layout()
        plt.savefig(OUT_DIR / "importancia_variables.png", dpi=130)
        plt.close()
        imp.rename("peso").to_csv(OUT_DIR / "importancia_variables.csv")
    except Exception as exc:  # pragma: no cover
        log.warning("No se pudo graficar importancia: %s", exc)


# ----------------------------------------------------------- persistencia BD
def persistir_predicciones(predicciones: pd.DataFrame) -> None:
    """Crea/refresca la tabla `predicciones` en Supabase como fuente del dashboard BI."""
    from carga_bd import _build_engine
    from sqlalchemy import text

    engine = _build_engine()
    ddl = text("""
        CREATE TABLE IF NOT EXISTS predicciones (
            customer_id   VARCHAR(20),
            churn_real    SMALLINT,
            churn_pred    SMALLINT,
            churn_proba   NUMERIC(6,4),
            acierto       BOOLEAN,
            modelo        VARCHAR(40),
            fecha         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE predicciones ENABLE ROW LEVEL SECURITY;
    """)
    with engine.begin() as conn:
        conn.execute(ddl)
        conn.execute(text("TRUNCATE TABLE predicciones"))
    predicciones.to_sql("predicciones", engine, if_exists="append", index=False, method="multi")
    log.info("Persistidas %d predicciones en Supabase (tabla predicciones)", len(predicciones))


# --------------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser(description="Entrena y evalua el modelo de churn")
    parser.add_argument("--fuente", choices=["csv", "supabase"], default="csv")
    parser.add_argument("--persistir", action="store_true",
                        help="Sube las predicciones a la tabla `predicciones` de Supabase")
    args = parser.parse_args()

    df = cargar_datos(args.fuente)
    analisis_exploratorio(df)
    res = entrenar_y_evaluar(df)
    if args.persistir:
        persistir_predicciones(res["predicciones"])
    log.info("Modelado completado. Artefactos en %s", OUT_DIR.relative_to(PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover
        log.error("Fallo en modelado: %s", exc, exc_info=True)
        sys.exit(1)
