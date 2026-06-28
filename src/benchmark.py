"""Análisis de rendimiento (Evaluación 3, apartado f — "Rendimiento nube").

Mide con `time.time()` + `psutil` el costo de las operaciones del flujo de
modelado, comparando la **lectura local (CSV)** vs la **lectura en la nube
(Supabase)** sobre el MISMO dataset, más el tiempo de entrenamiento.

Es una medición ligera (no un benchmark de escalado): para 7.043 filas el
flujo corre en segundos; el objetivo es ubicar el cuello de botella e ilustrar
el costo de la latencia de red de la nube.

Ejecutar:  python src/benchmark.py
Salidas:   outputs/rendimiento/  (tabla csv + gráfico png + json)
"""
from __future__ import annotations

import glob
import json
import os
import time
from pathlib import Path

import matplotlib
import pandas as pd
import psutil

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "outputs" / "rendimiento"
OUT.mkdir(parents=True, exist_ok=True)
load_dotenv(PROJECT_ROOT / ".env")

proc = psutil.Process()


def _rss_mb() -> float:
    return round(proc.memory_info().rss / 1024 / 1024, 1)


def _cron(fn):
    """Ejecuta fn() y devuelve (resultado, segundos)."""
    t0 = time.time()
    r = fn()
    return r, round(time.time() - t0, 3)


def leer_csv() -> pd.DataFrame:
    ruta = sorted(glob.glob(str(PROJECT_ROOT / "data" / "validated" / "telco_churn_valid_*.csv")))[-1]
    return pd.read_csv(ruta)


def leer_supabase() -> pd.DataFrame:
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    eng = create_engine(url, future=True, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    return pd.read_sql("SELECT * FROM clientes", eng)


def entrenar(df: pd.DataFrame):
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    df = df.copy()
    df["Churn"] = df["Churn"].astype(int) if "Churn" in df.columns else df["churn"].astype(int)
    target = "Churn" if "Churn" in df.columns else "churn"
    drop = [c for c in ["customerID", "customer_id", target, "tenure_group", "fecha_ingesta"] if c in df.columns]
    X = df.drop(columns=drop)
    X[X.select_dtypes(include="bool").columns] = X.select_dtypes(include="bool").astype(int)
    num = [c for c in ["tenure", "monthly_charges", "total_charges", "MonthlyCharges", "TotalCharges"] if c in X.columns]
    cat = [c for c in X.columns if c not in num and X[c].dtype == "object"]
    pre = ColumnTransformer([
        ("num", StandardScaler(), num),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
    ], remainder="passthrough")
    Xtr, _, ytr, _ = train_test_split(X, df[target], test_size=0.3, stratify=df[target], random_state=42)
    Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))]).fit(Xtr, ytr)


def main() -> int:
    rss0 = _rss_mb()
    psutil.cpu_percent(interval=None)  # primer llamado, descartar

    df_csv, t_csv = _cron(leer_csv)
    df_sb, t_sb = _cron(leer_supabase)
    _, t_train = _cron(lambda: entrenar(df_sb))

    cpu = psutil.cpu_percent(interval=0.3)
    rss = _rss_mb()

    filas = [
        {"operacion": "Lectura local (CSV)", "segundos": t_csv, "filas": len(df_csv)},
        {"operacion": "Lectura nube (Supabase)", "segundos": t_sb, "filas": len(df_sb)},
        {"operacion": "Entrenamiento modelo", "segundos": t_train, "filas": len(df_sb)},
    ]
    tabla = pd.DataFrame(filas)
    tabla.to_csv(OUT / "benchmark.csv", index=False)

    overhead = round(t_sb / t_csv, 1) if t_csv else None
    resumen = {
        "ram_rss_mb": rss, "ram_delta_mb": round(rss - rss0, 1), "cpu_pct": cpu,
        "overhead_nube_vs_local_x": overhead, "operaciones": filas,
        "total_segundos": round(t_csv + t_sb + t_train, 3),
    }
    with open(OUT / "benchmark.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    plt.figure(figsize=(6.5, 3.6))
    plt.barh(tabla["operacion"], tabla["segundos"], color=["#22c55e", "#1e3a8a", "#ef4444"])
    for i, v in enumerate(tabla["segundos"]):
        plt.text(v, i, f" {v}s", va="center", fontsize=9)
    plt.xlabel("segundos")
    plt.title("Rendimiento por operación (7.043 filas)")
    plt.tight_layout()
    plt.savefig(OUT / "benchmark.png", dpi=130)
    plt.close()

    print(tabla.to_string(index=False))
    print(f"\nRAM RSS: {rss} MB (Δ {rss-rss0:+.1f}) | CPU: {cpu}% | "
          f"Lectura nube {overhead}x más lenta que local | total {resumen['total_segundos']}s")
    print(f"Artefactos en {OUT.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
