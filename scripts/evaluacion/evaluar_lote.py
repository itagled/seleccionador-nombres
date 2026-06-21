#!/usr/bin/env python3
"""Evalua en lote nombres (v2: modos corto y completo)."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_OUTPUTS, DATA_RAW, setup_lib

setup_lib()

from evaluar_combinacion import resolver_fonetica
from export_csv import campos_csv, fila_modo
from fonetica_scoring import evaluar_combinacion, obtener_lexico

DB_PATH = DATA_DB


def parsear_archivo_nombres(ruta: Path) -> list[tuple[str, str]]:
    entradas: list[tuple[str, str]] = []
    vistos: set[tuple[str, str]] = set()
    genero: str | None = None

    for linea in ruta.read_text(encoding="utf-8").splitlines():
        texto = linea.strip()
        if not texto or texto.startswith("fuente:") or texto.startswith("descripción:"):
            continue
        if texto == "niña:":
            genero = "F"
            continue
        if texto == "niño:":
            genero = "M"
            continue
        if genero is None:
            continue
        clave = (texto, genero)
        if clave in vistos:
            continue
        vistos.add(clave)
        entradas.append(clave)

    return entradas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evalua un lote de nombres contra dos apellidos fijos (v2)."
    )
    parser.add_argument(
        "--archivo",
        type=Path,
        default=DATA_RAW / "ergobaby-2024.txt",
        help="Archivo con secciones niña:/niño:",
    )
    parser.add_argument("--apellido1", default="Tagle", help="Primer apellido")
    parser.add_argument("--apellido2", default="Díaz", help="Segundo apellido")
    parser.add_argument(
        "--modo-orden",
        choices=("corto", "completo"),
        default="corto",
        help="Columna nota_final usada para ordenar el CSV",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=DATA_OUTPUTS / "ergobaby_tagle_diaz.csv",
        help="CSV UTF-8 de salida",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.archivo.is_file():
        print(f"No se encontro el archivo: {args.archivo}", file=sys.stderr)
        return 1
    if not DB_PATH.exists():
        print(f"No se encontro la base de datos: {DB_PATH}", file=sys.stderr)
        return 1

    nombres = parsear_archivo_nombres(args.archivo)
    if not nombres:
        print("No se encontraron nombres en el archivo.", file=sys.stderr)
        return 1

    filas: list[dict[str, str | float | None]] = []

    with sqlite3.connect(DB_PATH) as conn:
        lexico = obtener_lexico(conn)
        ipa_ap1, _ = resolver_fonetica(conn, args.apellido1, None, es_nombre=False)
        ipa_ap2, _ = resolver_fonetica(conn, args.apellido2, None, es_nombre=False)

        for nombre, genero in nombres:
            ipa_nombre, _ = resolver_fonetica(conn, nombre, genero, es_nombre=True)
            resultado = evaluar_combinacion(
                nombre,
                args.apellido1,
                args.apellido2,
                (ipa_nombre, ipa_ap1, ipa_ap2),
                lexico=lexico,
            )
            fila: dict[str, str | float | None] = {
                "nombre": nombre,
                "genero": genero,
                "apellido1": args.apellido1,
                "apellido2": args.apellido2,
                "fonetica_nombre": resultado.piezas[0],
            }
            fila.update(fila_modo(resultado.corto, "corto"))
            fila.update(fila_modo(resultado.completo, "completo"))
            filas.append(fila)

    clave_orden = f"{args.modo_orden}_nota_final"
    filas.sort(key=lambda f: (-float(f[clave_orden]), str(f["nombre"])))

    campos = campos_csv()
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filas)

    print(f"Evaluados {len(filas)} nombres -> {args.salida}")
    print(
        f"Top 5 ({args.modo_orden}): "
        + ", ".join(f"{r['nombre']} ({r[clave_orden]})" for r in filas[:5])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
