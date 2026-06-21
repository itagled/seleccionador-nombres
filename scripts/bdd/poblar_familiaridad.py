#!/usr/bin/env python3
"""Pobla la tabla familiaridad desde guaguas.csv (prevalencia ponderada por recencia)."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, setup_lib

setup_lib()

from familiaridad import (
    EPS,
    GUAGUAS_CSV,
    calcular_familiaridad_guaguas,
    familiaridad_de,
    poblar_tabla_familiaridad,
)

DEFAULT_DB_PATH = DATA_DB

VERIFICACION = [
    ("MARÍA", "F"),
    ("JUAN", "M"),
    ("JOSÉ", "M"),
    ("MATEO", "M"),
    ("MARTINA", "F"),
    ("SOFÍA", "F"),
    ("BENJAMÍN", "M"),
    ("CASIMIRO", "M"),
    ("EDMUNDO", "M"),
    ("BALTASAR", "M"),
    ("DEMETRIO", "M"),
    ("BEGOÑA", "F"),
]


def get_db_path() -> Path:
    if ruta := os.environ.get("SQLITE_PATH"):
        return Path(ruta)
    return DEFAULT_DB_PATH


def imprimir_verificacion(conn: sqlite3.Connection) -> None:
    print("\n--- Verificación log_familiaridad (ordenado) ---")
    filas: list[tuple[str, str, float, float, float | None]] = []
    for nombre, genero in VERIFICACION:
        row = conn.execute(
            """
            SELECT n.nombre, n.genero, f.prevalencia, f.log_familiaridad, f.prop_reciente
            FROM nombres n
            LEFT JOIN familiaridad f ON f.nombre_id = n.id
            WHERE n.nombre = ? AND n.genero = ?
            LIMIT 1
            """,
            (nombre, genero),
        ).fetchone()
        if row:
            filas.append(row)
        else:
            prev, log_f, _ = familiaridad_de(nombre, genero, conn=conn)
            filas.append((nombre, genero, prev, log_f, None))

    filas.sort(key=lambda r: r[3], reverse=True)
    print(f"{'nombre':<12} {'G':>1}  {'prevalencia':>12}  {'log_fam':>10}  {'prop_rec':>10}")
    for nombre, genero, prev, log_f, prop_rec in filas:
        prop_txt = f"{prop_rec:.6f}" if prop_rec is not None else "—"
        print(f"{nombre:<12} {genero:>1}  {prev:12.6f}  {log_f:10.4f}  {prop_txt:>10}")
    print(f"\nPiso log(EPS) = {__import__('math').log(EPS):.4f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pobla familiaridad desde guaguas.csv.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=GUAGUAS_CSV,
        help="Ruta a guaguas.csv",
    )
    args = parser.parse_args()

    db_path = get_db_path()
    if not db_path.is_file():
        print(f"No se encontró la base de datos: {db_path}", file=sys.stderr)
        return 1
    if not args.csv.is_file():
        print(f"No se encontró guaguas.csv: {args.csv}", file=sys.stderr)
        return 1

    inicio = time.perf_counter()
    print(f"Calculando prevalencia desde {args.csv} ...")
    stats = calcular_familiaridad_guaguas(str(args.csv))
    print(f"  tokens (nombre, genero) en guaguas: {len(stats):,}")

    with sqlite3.connect(db_path) as conn:
        insertados = poblar_tabla_familiaridad(conn, stats)
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM familiaridad").fetchone()[0]
        print(f"Filas en familiaridad: {total:,} (insertadas {insertados:,})")
        imprimir_verificacion(conn)

    print(f"\nTiempo total: {time.perf_counter() - inicio:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
