#!/usr/bin/env python3
"""Exporta el vector de features ML (5 ejes + one-hot tipo_contacto) a CSV."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluacion"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_OUTPUTS, setup_lib

setup_lib()

from evaluar_combinacion import resolver_fonetica
from features_ml import campos_csv_export, fila_features_ml
from fonetica_scoring import extraer_features, obtener_lexico

CASOS_DEFAULT = [
    ("Luna", "F", "García", "Romero"),
    ("Carmen", "F", "García", "Romero"),
    ("David", "M", "García", "Romero"),
    ("Sofía", "F", "Tagle", "Díaz"),
    ("Ramón", "M", "Calderón", "Pinto"),
]


def cargar_combos(ruta: Path) -> list[tuple[str, str, str, str]]:
    combos: list[tuple[str, str, str, str]] = []
    with ruta.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            combos.append(
                (
                    row["nombre"].strip(),
                    row["genero"].strip().upper(),
                    row["apellido1"].strip(),
                    row["apellido2"].strip(),
                )
            )
    return combos


def exportar_filas(
    conn: sqlite3.Connection,
    combos: list[tuple[str, str, str, str]],
) -> list[dict[str, str | int | float]]:
    lexico = obtener_lexico(conn)
    filas: list[dict[str, str | int | float]] = []
    for nombre, genero, ap1, ap2 in combos:
        ipa_n, _ = resolver_fonetica(conn, nombre, genero, es_nombre=True)
        ipa_a1, _ = resolver_fonetica(conn, ap1, None, es_nombre=False)
        ipa_a2, _ = resolver_fonetica(conn, ap2, None, es_nombre=False)
        feat = extraer_features(
            nombre,
            ap1,
            ap2,
            (ipa_n, ipa_a1, ipa_a2),
            genero,
            lexico=lexico,
            conn=conn,
        )
        filas.append(
            fila_features_ml(
                feat,
                genero=genero,
                ipa_nombre=ipa_n,
                ipa_ap1=ipa_a1,
                ipa_ap2=ipa_a2,
            )
        )
    return filas


def escribir_csv(ruta: Path, filas: list[dict[str, str | int | float]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    campos = campos_csv_export()
    with ruta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta features ML a CSV.")
    parser.add_argument("--nombre", help="Nombre a evaluar")
    parser.add_argument("--genero", choices=("M", "F"), help="Genero M/F")
    parser.add_argument("--apellido1", help="Primer apellido")
    parser.add_argument("--apellido2", help="Segundo apellido")
    parser.add_argument(
        "--input",
        type=Path,
        help="CSV con columnas nombre,genero,apellido1,apellido2",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_OUTPUTS / "features_export.csv",
        help="Ruta de salida CSV",
    )
    args = parser.parse_args()

    if args.input:
        combos = cargar_combos(args.input)
    elif args.nombre and args.genero and args.apellido1 and args.apellido2:
        combos = [(args.nombre, args.genero, args.apellido1, args.apellido2)]
    else:
        combos = CASOS_DEFAULT

    if not DATA_DB.is_file():
        print(f"No se encontro la base de datos: {DATA_DB}", file=sys.stderr)
        return 1

    with sqlite3.connect(DATA_DB) as conn:
        filas = exportar_filas(conn, combos)

    escribir_csv(args.output, filas)
    print(f"Exportadas {len(filas)} filas -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
