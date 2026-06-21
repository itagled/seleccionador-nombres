#!/usr/bin/env python3
"""Agrega la columna fonetica y la rellena con phonemizer + espeak-ng."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, ROOT, setup_lib

setup_lib()

from phonemizer_config import FONETICA_LANGUAGE, fonetizar_nombres

DEFAULT_DB_PATH = DATA_DB
BATCH_SIZE = 500


def get_db_path() -> Path:
    if ruta := os.environ.get("SQLITE_PATH"):
        return Path(ruta)
    return DEFAULT_DB_PATH


def columna_existe(conn: sqlite3.Connection, columna: str) -> bool:
    columnas = conn.execute("PRAGMA table_info(nombres)").fetchall()
    return any(fila[1] == columna for fila in columnas)


def aplicar_migracion(conn: sqlite3.Connection) -> None:
    if not columna_existe(conn, "fonetica"):
        conn.execute("ALTER TABLE nombres ADD COLUMN fonetica TEXT")
        print("Columna fonetica agregada.")


def nombres_pendientes(
    conn: sqlite3.Connection,
    forzar: bool,
    limite: int | None,
) -> list[str]:
    if forzar:
        query = "SELECT DISTINCT nombre FROM nombres ORDER BY nombre"
    else:
        query = "SELECT DISTINCT nombre FROM nombres WHERE fonetica IS NULL ORDER BY nombre"

    if limite is not None:
        query += f" LIMIT {int(limite)}"

    return [fila[0] for fila in conn.execute(query).fetchall()]


def guardar_fonetica(
    conn: sqlite3.Connection,
    nombre: str,
    fonetica: str,
    forzar: bool,
) -> int:
    if forzar:
        cur = conn.execute(
            "UPDATE nombres SET fonetica = ? WHERE nombre = ?",
            (fonetica, nombre),
        )
    else:
        cur = conn.execute(
            "UPDATE nombres SET fonetica = ? WHERE nombre = ? AND fonetica IS NULL",
            (fonetica, nombre),
        )
    return cur.rowcount


def poblar(
    conn: sqlite3.Connection,
    pendientes: list[str],
    forzar: bool,
) -> tuple[int, int, int, float]:
    actualizados = 0
    errores = 0
    total = len(pendientes)
    inicio = time.perf_counter()

    for offset in range(0, total, BATCH_SIZE):
        lote = pendientes[offset : offset + BATCH_SIZE]
        try:
            foneticas = fonetizar_nombres(lote)
        except Exception as exc:
            print(f"Error en lote {offset}-{offset + len(lote)}: {exc}", file=sys.stderr)
            for nombre in lote:
                try:
                    fonetica = fonetizar_nombres([nombre])[0]
                    actualizados += guardar_fonetica(conn, nombre, fonetica, forzar)
                except Exception as nombre_exc:
                    errores += 1
                    print(f"  fallo '{nombre}': {nombre_exc}", file=sys.stderr)
            conn.commit()
            continue

        if len(foneticas) != len(lote):
            raise RuntimeError(
                f"phonemizer devolvio {len(foneticas)} resultados para {len(lote)} nombres"
            )

        for nombre, fonetica in zip(lote, foneticas, strict=True):
            actualizados += guardar_fonetica(conn, nombre, fonetica, forzar)

        conn.commit()
        hechos = min(offset + len(lote), total)
        elapsed = time.perf_counter() - inicio
        print(f"  {hechos:,}/{total:,} nombres unicos procesados ({elapsed:.1f}s)")

    tiempo_total = time.perf_counter() - inicio
    return total, actualizados, errores, tiempo_total


def imprimir_resumen(conn: sqlite3.Connection) -> None:
    total = conn.execute("SELECT COUNT(*) FROM nombres").fetchone()[0]
    con_fonetica = conn.execute(
        "SELECT COUNT(*) FROM nombres WHERE fonetica IS NOT NULL"
    ).fetchone()[0]
    sin_fonetica = total - con_fonetica
    print(f"\nTotal filas: {total:,}")
    print(f"Con fonetica: {con_fonetica:,}")
    print(f"Sin fonetica: {sin_fonetica:,}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pobla la columna fonetica en nombres.db usando phonemizer."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recalcula fonetica aunque ya exista.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Procesa solo N nombres unicos (util para pruebas).",
    )
    args = parser.parse_args()

    db_path = get_db_path()
    if not db_path.exists():
        print(f"No se encontro la base de datos: {db_path}", file=sys.stderr)
        return 1

    print(f"Base de datos: {db_path}")
    print(f"Dialecto espeak: {FONETICA_LANGUAGE}")
    inicio_corrida = time.perf_counter()

    with sqlite3.connect(db_path) as conn:
        aplicar_migracion(conn)
        conn.commit()

        pendientes = nombres_pendientes(conn, args.force, args.limit)
        if not pendientes:
            print("No hay nombres pendientes de fonetizar.")
            imprimir_resumen(conn)
            print(f"Tiempo total: {time.perf_counter() - inicio_corrida:.1f}s")
            return 0

        print(f"Nombres unicos a fonetizar: {len(pendientes):,}")
        procesados, filas_actualizadas, errores, tiempo_fonetica = poblar(
            conn, pendientes, args.force
        )

    tiempo_total = time.perf_counter() - inicio_corrida

    print(f"\nNombres unicos procesados: {procesados:,}")
    print(f"Filas actualizadas: {filas_actualizadas:,}")
    print(f"Tiempo total: {tiempo_total:.1f}s ({tiempo_total / 60:.1f} min)")
    print(f"  fonetizacion: {tiempo_fonetica:.1f}s")
    if procesados:
        print(f"  promedio: {tiempo_fonetica / procesados * 1000:.1f} ms por nombre unico")
    if errores:
        print(f"Errores: {errores:,}", file=sys.stderr)

    with sqlite3.connect(db_path) as conn:
        imprimir_resumen(conn)

    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
