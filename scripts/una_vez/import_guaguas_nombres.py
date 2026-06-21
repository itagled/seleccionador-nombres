#!/usr/bin/env python3
"""Agrega a nombres.db los pares (nombre, genero) de guaguas.csv que aun no existen."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, setup_lib

setup_lib()

DEFAULT_DB_PATH = DATA_DB

from nombres_sources import cargar_desde_guaguas, normalizar_nombre


def get_db_path() -> Path:
    if ruta := os.environ.get("SQLITE_PATH"):
        return Path(ruta)
    return DEFAULT_DB_PATH


def insertar_nombres(conn: sqlite3.Connection, pares: set[tuple[str, str]]) -> int:
    registros = sorted(pares, key=lambda par: (par[1], par[0]))
    conn.executemany(
        "INSERT INTO nombres (nombre, genero) VALUES (?, ?)",
        registros,
    )
    return len(registros)


def main() -> int:
    try:
        pares_guaguas = cargar_desde_guaguas()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    db_path = get_db_path()
    print(f"Nombres unicos en guaguas (nombre + genero): {len(pares_guaguas):,}")
    print(f"Base de datos: {db_path}")

    with sqlite3.connect(db_path) as conn:
        existentes = set(conn.execute("SELECT nombre, genero FROM nombres").fetchall())
        nuevos = pares_guaguas - existentes
        insertados = insertar_nombres(conn, nuevos) if nuevos else 0
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM nombres").fetchone()[0]
        print(f"Nombres nuevos insertados: {insertados:,}")
        print(f"Nombres que ya existian: {len(pares_guaguas) - len(nuevos):,}")
        print(f"Total en la tabla: {total:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
