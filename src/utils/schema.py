"""Esquema pandera para la validacion estructural del dataset Telco Churn.

Define tipos, rangos y valores permitidos. Se aplica DESPUES de la limpieza,
por lo que asume que TotalCharges ya es numerico y los Yes/No estan
normalizados a booleanos cuando corresponde.
"""
from __future__ import annotations

from pandera import Column, DataFrameSchema, Check


SERVICIOS_INTERNET_VALUES = ["Yes", "No", "No internet service"]
LINEAS_MULTIPLES_VALUES = ["Yes", "No", "No phone service"]


schema_clientes = DataFrameSchema(
    columns={
        "customerID": Column(
            str,
            checks=Check.str_matches(r"^\d{4}-[A-Z]{5}$"),
            nullable=False,
            unique=True,
        ),
        "gender": Column(str, checks=Check.isin(["Male", "Female"])),
        "SeniorCitizen": Column(int, checks=Check.isin([0, 1])),
        "Partner": Column(bool),
        "Dependents": Column(bool),
        "tenure": Column(int, checks=Check.in_range(0, 100)),
        "PhoneService": Column(bool),
        "MultipleLines": Column(str, checks=Check.isin(LINEAS_MULTIPLES_VALUES)),
        "InternetService": Column(str, checks=Check.isin(["DSL", "Fiber optic", "No"])),
        "OnlineSecurity": Column(str, checks=Check.isin(SERVICIOS_INTERNET_VALUES)),
        "OnlineBackup": Column(str, checks=Check.isin(SERVICIOS_INTERNET_VALUES)),
        "DeviceProtection": Column(str, checks=Check.isin(SERVICIOS_INTERNET_VALUES)),
        "TechSupport": Column(str, checks=Check.isin(SERVICIOS_INTERNET_VALUES)),
        "StreamingTV": Column(str, checks=Check.isin(SERVICIOS_INTERNET_VALUES)),
        "StreamingMovies": Column(str, checks=Check.isin(SERVICIOS_INTERNET_VALUES)),
        "Contract": Column(str, checks=Check.isin(["Month-to-month", "One year", "Two year"])),
        "PaperlessBilling": Column(bool),
        "PaymentMethod": Column(
            str,
            checks=Check.isin([
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ]),
        ),
        "MonthlyCharges": Column(float, checks=Check.in_range(0, 1000)),
        "TotalCharges": Column(float, checks=Check.in_range(0, 100_000), nullable=True),
        "tenure_group": Column(str, checks=Check.isin([
            "0-12", "13-24", "25-48", "49-72", "73+"
        ])),
        "Churn": Column(bool),
    },
    strict=True,
    coerce=False,
)


def validar_reglas_semanticas(row: dict) -> list[str]:
    """Aplica reglas de negocio cruzadas sobre una fila ya estructuralmente valida.

    Devuelve lista de motivos de rechazo. Lista vacia = fila valida.
    """
    motivos: list[str] = []

    sin_internet = row["InternetService"] == "No"
    servicios_internet = [
        "OnlineSecurity", "OnlineBackup", "DeviceProtection",
        "TechSupport", "StreamingTV", "StreamingMovies",
    ]
    for servicio in servicios_internet:
        if sin_internet and row[servicio] != "No internet service":
            motivos.append(
                f"{servicio}={row[servicio]} inconsistente con InternetService=No"
            )
        if not sin_internet and row[servicio] == "No internet service":
            motivos.append(
                f"{servicio}=No internet service inconsistente con InternetService={row['InternetService']}"
            )

    if not row["PhoneService"] and row["MultipleLines"] != "No phone service":
        motivos.append(
            f"MultipleLines={row['MultipleLines']} inconsistente con PhoneService=False"
        )
    if row["PhoneService"] and row["MultipleLines"] == "No phone service":
        motivos.append(
            "MultipleLines=No phone service inconsistente con PhoneService=True"
        )

    total_charges = row.get("TotalCharges")
    total_charges_es_nan = total_charges is None or (
        isinstance(total_charges, float) and total_charges != total_charges
    )

    if row["tenure"] > 0 and total_charges_es_nan:
        motivos.append(
            f"TotalCharges nulo no permitido cuando tenure={row['tenure']} (>0)"
        )

    if row["tenure"] > 0 and row["MonthlyCharges"] > 0 and not total_charges_es_nan:
        esperado_minimo = row["MonthlyCharges"] * 0.5
        if total_charges < esperado_minimo:
            motivos.append(
                f"TotalCharges={total_charges} muy bajo para tenure={row['tenure']} "
                f"con MonthlyCharges={row['MonthlyCharges']}"
            )

    return motivos
