"""Tests basicos de las reglas de validacion semantica.

Se ejecutan con: pytest tests/
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.schema import validar_reglas_semanticas


def _fila_base() -> dict:
    """Devuelve una fila valida con todos los servicios contratados."""
    return {
        "customerID": "0001-ABCDE",
        "gender": "Male",
        "SeniorCitizen": 0,
        "Partner": True,
        "Dependents": False,
        "tenure": 12,
        "PhoneService": True,
        "MultipleLines": "Yes",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "Yes",
        "OnlineBackup": "Yes",
        "DeviceProtection": "Yes",
        "TechSupport": "Yes",
        "StreamingTV": "Yes",
        "StreamingMovies": "Yes",
        "Contract": "One year",
        "PaperlessBilling": True,
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 80.0,
        "TotalCharges": 960.0,
        "tenure_group": "0-12",
        "Churn": False,
    }


def test_fila_valida_no_devuelve_motivos():
    motivos = validar_reglas_semanticas(_fila_base())
    assert motivos == []


def test_internet_no_obliga_servicios_no_internet_service():
    fila = _fila_base()
    fila["InternetService"] = "No"
    motivos = validar_reglas_semanticas(fila)
    assert any("OnlineSecurity" in m for m in motivos)


def test_internet_si_no_acepta_no_internet_service():
    fila = _fila_base()
    fila["OnlineSecurity"] = "No internet service"
    motivos = validar_reglas_semanticas(fila)
    assert any("OnlineSecurity" in m for m in motivos)


def test_sin_phone_service_multiple_lines_debe_ser_no_phone_service():
    fila = _fila_base()
    fila["PhoneService"] = False
    fila["MultipleLines"] = "Yes"
    motivos = validar_reglas_semanticas(fila)
    assert any("MultipleLines" in m for m in motivos)


def test_phone_service_no_acepta_no_phone_service():
    fila = _fila_base()
    fila["PhoneService"] = True
    fila["MultipleLines"] = "No phone service"
    motivos = validar_reglas_semanticas(fila)
    assert any("MultipleLines" in m for m in motivos)


def test_combinacion_internet_no_correcta_pasa():
    fila = _fila_base()
    fila["InternetService"] = "No"
    for s in ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
              "TechSupport", "StreamingTV", "StreamingMovies"]:
        fila[s] = "No internet service"
    motivos = validar_reglas_semanticas(fila)
    assert motivos == []
