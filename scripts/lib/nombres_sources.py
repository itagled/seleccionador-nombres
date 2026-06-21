#!/usr/bin/env python3
"""Funciones compartidas para extraer pares (nombre, genero) desde las fuentes."""

from __future__ import annotations

import csv

from bootstrap import DATA_RAW

CSV_ESPANIA = {
    "M": DATA_RAW / "nombres-masculinos-frecuencia-edad-2012.csv",
    "F": DATA_RAW / "nombres-femeninos-frecuencia-edad-2012.csv",
}
GUAGUAS_CSV = DATA_RAW / "guaguas.csv"
EDAD_MEDIA_XLSX = DATA_RAW / "nombres_por_edad_media.xlsx"


def normalizar_nombre(nombre: str) -> str:
    return nombre.strip().upper()


def extraer_tokens(nombre: str) -> list[str]:
    return [token for token in nombre.strip().split() if token]


def agregar_tokens(pares: set[tuple[str, str]], nombre: str, genero: str) -> None:
    for token in extraer_tokens(nombre):
        pares.add((normalizar_nombre(token), genero))


def cargar_desde_csv_espania() -> set[tuple[str, str]]:
    pares: set[tuple[str, str]] = set()

    for genero, csv_path in CSV_ESPANIA.items():
        if not csv_path.exists():
            raise FileNotFoundError(f"No se encontro el archivo: {csv_path}")

        with csv_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                agregar_tokens(pares, row["nombre"], genero)

    return pares


def cargar_desde_guaguas() -> set[tuple[str, str]]:
    if not GUAGUAS_CSV.exists():
        raise FileNotFoundError(f"No se encontro el archivo: {GUAGUAS_CSV}")

    pares: set[tuple[str, str]] = set()
    with GUAGUAS_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            genero = row["sexo"].strip()
            if genero not in {"M", "F"}:
                continue
            agregar_tokens(pares, row["nombre"], genero)

    return pares


def cargar_desde_edad_media_xlsx() -> set[tuple[str, str]]:
    if not EDAD_MEDIA_XLSX.exists():
        raise FileNotFoundError(f"No se encontro el archivo: {EDAD_MEDIA_XLSX}")

    import pandas as pd

    pares: set[tuple[str, str]] = set()
    hojas = {
        "Hombres": "M",
        "Mujeres": "F",
    }

    for hoja, genero in hojas.items():
        df = pd.read_excel(EDAD_MEDIA_XLSX, sheet_name=hoja, header=6)
        for nombre in df["Nombre"].dropna().astype(str):
            agregar_tokens(pares, nombre, genero)

    return pares


def cargar_todos_los_nombres() -> dict[str, set[tuple[str, str]]]:
    return {
        "espania_2012": cargar_desde_csv_espania(),
        "guaguas": cargar_desde_guaguas(),
        "edad_media_2025": cargar_desde_edad_media_xlsx(),
    }
