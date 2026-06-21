#!/usr/bin/env python3
"""Carga pares T2 desde pilot_pares.csv si la tabla está vacía."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from db import conectar, contar_pares, ensure_schema, obtener_database_url

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_CSV = REPO_ROOT / "data" / "intermedio" / "pilot_pares.csv"


def forma_completa(nombre: str, apellido1: str) -> str:
    return f"{nombre} {apellido1}"


def cargar_filas_t2() -> list[dict[str, str]]:
    if not PILOT_CSV.is_file():
        raise FileNotFoundError(f"No se encontró el CSV del pilot: {PILOT_CSV}")
    filas: list[dict[str, str]] = []
    with PILOT_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("tipo") != "T2":
                continue
            ap1 = row["apellido1"].strip()
            filas.append(
                {
                    "tipo": "T2",
                    "genero": row["genero"].strip().upper(),
                    "apellido1": ap1,
                    "apellido2": (row.get("apellido2") or "").strip() or None,
                    "nombre_a": row["nombre_a"].strip(),
                    "nombre_b": row["nombre_b"].strip(),
                    "forma_a": forma_completa(row["nombre_a"].strip(), ap1),
                    "forma_b": forma_completa(row["nombre_b"].strip(), ap1),
                    "estrategia": (row.get("estrategia") or "").strip() or None,
                }
            )
    return filas


def seed_if_empty() -> int:
    ensure_schema()
    existentes = contar_pares()
    if existentes > 0:
        return existentes

    filas = cargar_filas_t2()
    if not filas:
        raise RuntimeError("No hay filas T2 en pilot_pares.csv")

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO pares (
                    tipo, genero, apellido1, apellido2,
                    nombre_a, nombre_b, forma_a, forma_b, estrategia
                ) VALUES (
                    %(tipo)s, %(genero)s, %(apellido1)s, %(apellido2)s,
                    %(nombre_a)s, %(nombre_b)s, %(forma_a)s, %(forma_b)s, %(estrategia)s
                )
                """,
                filas,
            )
        conn.commit()

    return len(filas)


def main() -> int:
    try:
        _ = obtener_database_url()
        insertados = seed_if_empty()
        if insertados == contar_pares() and contar_pares() > 0:
            print(f"Seed OK: {insertados} pares T2 en la base.")
        else:
            print(f"La base ya tenía pares ({contar_pares()} filas); no se insertó nada.")
        return 0
    except Exception as exc:
        print(f"Error en seed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
