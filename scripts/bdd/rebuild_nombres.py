#!/usr/bin/env python3
"""Reconstruye la tabla nombres desde todas las fuentes, conservando tildes."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, ROOT, setup_lib

setup_lib()

DEFAULT_DB_PATH = DATA_DB
SCHEMA_FILE = ROOT / "schema" / "001_nombres.sql"

from nombres_sources import cargar_todos_los_nombres


def get_db_path() -> Path:
    if ruta := os.environ.get("SQLITE_PATH"):
        return Path(ruta)
    return DEFAULT_DB_PATH


def aplicar_esquema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))


def limpiar_tabla(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM nombres")
    conn.execute("DELETE FROM sqlite_sequence WHERE name = 'nombres'")


def insertar_nombres(conn: sqlite3.Connection, pares: set[tuple[str, str]]) -> int:
    registros = sorted(pares, key=lambda par: (par[1], par[0]))
    conn.executemany(
        "INSERT INTO nombres (nombre, genero) VALUES (?, ?)",
        registros,
    )
    return len(registros)


def imprimir_resumen(conn: sqlite3.Connection, por_fuente: dict[str, set[tuple[str, str]]]) -> None:
    total = conn.execute("SELECT COUNT(*) FROM nombres").fetchone()[0]
    por_genero = conn.execute(
        "SELECT genero, COUNT(*) FROM nombres GROUP BY genero ORDER BY genero"
    ).fetchall()
    en_ambos_generos = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT nombre
            FROM nombres
            GROUP BY nombre
            HAVING COUNT(DISTINCT genero) = 2
        )
        """
    ).fetchone()[0]
    con_tilde = conn.execute(
        """
        SELECT COUNT(*)
        FROM nombres
        WHERE nombre LIKE '%Á%' OR nombre LIKE '%É%' OR nombre LIKE '%Í%'
           OR nombre LIKE '%Ó%' OR nombre LIKE '%Ú%' OR nombre LIKE '%Ñ%'
           OR nombre LIKE '%Ü%'
        """
    ).fetchone()[0]

    print("\nContribucion por fuente (pares unicos en cada una):")
    for fuente, pares in por_fuente.items():
        print(f"  {fuente}: {len(pares):,}")

    print(f"\nTotal en la tabla: {total:,}")
    for genero, cantidad in por_genero:
        etiqueta = "masculino" if genero == "M" else "femenino"
        print(f"  {etiqueta} ({genero}): {cantidad:,}")
    print(f"Nombres distintos en M y F: {en_ambos_generos:,}")
    print(f"Nombres con tilde o ene: {con_tilde:,}")


def main() -> int:
    try:
        por_fuente = cargar_todos_los_nombres()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    pares = set().union(*por_fuente.values())
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Pares unicos combinados (nombre + genero): {len(pares):,}")
    print(f"Base de datos: {db_path}")

    with sqlite3.connect(db_path) as conn:
        aplicar_esquema(conn)
        limpiar_tabla(conn)
        insertados = insertar_nombres(conn, pares)
        conn.commit()
        print(f"Importacion completada: {insertados:,} filas.")
        imprimir_resumen(conn, por_fuente)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
