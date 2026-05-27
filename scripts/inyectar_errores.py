"""Genera un dataset con errores intencionales para la DEMO en vivo.

Toma el CSV original limpio del caso y le inyecta varios tipos de errores
para demostrar que el pipeline los detecta y rechaza correctamente.

Uso:
    python scripts/inyectar_errores.py

Genera: data/raw/telco_churn_demo_con_errores.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUENTE = PROJECT_ROOT.parent / "0.CASOS_PARCIALES_Evaluaciones-2y3" / "01_Telco Customer Churn" / "02_Base_WA_Fn-UseC_-Telco-Customer-Churn.csv"
DESTINO = PROJECT_ROOT / "data" / "raw" / "telco_churn_demo_con_errores.csv"


def inyectar() -> Path:
    df = pd.read_csv(FUENTE)

    # Toma 50 filas para hacer el dataset manejable en la demo
    df_demo = df.head(50).copy().reset_index(drop=True)

    # ERROR ESTRUCTURAL 1: gender invalido
    df_demo.loc[2, "gender"] = "Otro"

    # ERROR ESTRUCTURAL 2: tenure fuera de rango
    df_demo.loc[5, "tenure"] = 999

    # ERROR ESTRUCTURAL 3: Contract invalido
    df_demo.loc[8, "Contract"] = "3 years"

    # ERROR ESTRUCTURAL 4: customerID con formato invalido
    df_demo.loc[11, "customerID"] = "INVALIDO"

    # ERROR ESTRUCTURAL 5: MonthlyCharges negativo
    df_demo.loc[14, "MonthlyCharges"] = -50.0

    # ERROR SEMANTICO 1: InternetService=No pero OnlineSecurity=Yes
    df_demo.loc[17, "InternetService"] = "No"
    df_demo.loc[17, "OnlineSecurity"] = "Yes"

    # ERROR SEMANTICO 2: PhoneService=Yes pero MultipleLines=No phone service
    df_demo.loc[20, "PhoneService"] = "Yes"
    df_demo.loc[20, "MultipleLines"] = "No phone service"

    # ERROR SEMANTICO 3: TotalCharges=0 con tenure alto
    df_demo.loc[23, "tenure"] = 24
    df_demo.loc[23, "MonthlyCharges"] = 75.0
    df_demo.loc[23, "TotalCharges"] = 5.0

    # Resto de las 50 filas quedan limpias
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    df_demo.to_csv(DESTINO, index=False)
    print(f"Dataset con errores generado en: {DESTINO}")
    print(f"Total filas: {len(df_demo)} (8 con errores intencionales)")
    return DESTINO


if __name__ == "__main__":
    inyectar()
