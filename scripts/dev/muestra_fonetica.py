#!/usr/bin/env python3
"""Muestra de fonetizacion con phonemizer + espeak-ng."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_OUTPUTS, setup_lib
from phonemizer_config import fonetizar_texto

setup_lib()

DB_PATH = DATA_DB
OUTPUT_CSV = DATA_OUTPUTS / "muestra_fonetica_100.csv"


def seleccionar_muestra(conn: sqlite3.Connection, n: int = 100) -> list[tuple[str, str]]:
    curiosos = [
        "MARIA", "MARÍA", "JOSE", "JOSÉ", "ANTONIO", "GARCÍA", "IÑIGO",
        "MILLARAY", "ANTONELLA", "BENJAMÍN", "SOFÍA", "MARTÍN", "ÁNGEL",
        "LUCIA", "LUCÍA", "ANDRES", "ANDRÉS", "FELIX", "FÉLIX", "RAFAEL",
        "CARMEN", "DOLORES", "CONCEPCIÓN", "JAVIER", "ALEJANDRO", "FERNANDO",
        "RODRIGO", "GONZALO", "IGNACIO", "SEBASTIÁN", "VALENTINA", "ISIDORA",
        "MAITE", "XIMENA", "BEGOÑA", "ITZIAR", "NEREA", "AINHOA", "GAEL",
        "LEIRE", "IKER", "UNAX", "ENEKO", "JUNE", "DAIANA", "YASMIN",
        "MOHAMED", "FATIMA", "AISHA", "KIMBERLY", "BRIAN", "KEVIN",
    ]

    sample: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    placeholders = ",".join("?" for _ in curiosos)
    for row in conn.execute(
        f"SELECT nombre, genero FROM nombres WHERE nombre IN ({placeholders}) ORDER BY nombre, genero",
        curiosos,
    ):
        if row not in seen:
            seen.add(row)
            sample.append(row)

    for row in conn.execute(
        """
        SELECT nombre, genero FROM nombres
        WHERE nombre LIKE '%Á%' OR nombre LIKE '%É%' OR nombre LIKE '%Í%'
           OR nombre LIKE '%Ó%' OR nombre LIKE '%Ú%' OR nombre LIKE '%Ñ%'
        ORDER BY RANDOM()
        LIMIT 30
        """
    ):
        if row not in seen:
            seen.add(row)
            sample.append(row)

    faltan = n - len(sample)
    if faltan > 0:
        for row in conn.execute(
            "SELECT nombre, genero FROM nombres ORDER BY RANDOM() LIMIT ?",
            (faltan * 2,),
        ):
            if row not in seen:
                seen.add(row)
                sample.append(row)
            if len(sample) >= n:
                break

    return sample[:n]


def main() -> int:
    if not DB_PATH.exists():
        print(f"No se encontro la base de datos: {DB_PATH}", file=sys.stderr)
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        muestra = seleccionar_muestra(conn)

    filas: list[dict[str, str]] = []
    for nombre, genero in muestra:
        texto = nombre.title()
        filas.append(
            {
                "nombre": nombre,
                "genero": genero,
                "fonetica": fonetizar_texto(texto, language="es"),
            }
        )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["nombre", "genero", "fonetica"],
        )
        writer.writeheader()
        writer.writerows(filas)

    print(f"Muestra generada con phonemizer: {len(filas)} nombres -> {OUTPUT_CSV}")
    print("\nPrimeros 15 ejemplos:\n")
    print(f"{'NOMBRE':<18} {'G':<2} {'FONETICA (IPA)'}")
    print("-" * 60)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        print("(Ver ejemplos completos en el CSV; la consola no muestra bien los simbolos IPA.)")
    else:
        for fila in filas[:15]:
            print(f"{fila['nombre']:<18} {fila['genero']:<2} {fila['fonetica']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
