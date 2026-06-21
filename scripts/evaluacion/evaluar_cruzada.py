#!/usr/bin/env python3
"""Evaluacion cruzada: nombres x pares de apellidos (v2, CSV completo)."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_INTERMEDIO, DATA_OUTPUTS, DATA_RAW, setup_lib

setup_lib()

from evaluar_combinacion import resolver_fonetica
from evaluar_lote import parsear_archivo_nombres
from export_csv import campos_csv, fila_modo
from fonetica_scoring import evaluar_combinacion, obtener_lexico

DB_PATH = DATA_DB


def nombres_balanceados(
    entradas: list[tuple[str, str]], por_genero: int
) -> list[tuple[str, str]]:
    femeninos = [e for e in entradas if e[1] == "F"]
    masculinos = [e for e in entradas if e[1] == "M"]
    return femeninos[:por_genero] + masculinos[:por_genero]


def parsear_pares(ruta: Path) -> list[tuple[str, str]]:
    pares: list[tuple[str, str]] = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        texto = linea.strip()
        if not texto or texto.startswith("#"):
            continue
        partes = texto.split("\t")
        if len(partes) != 2:
            partes = [p.strip() for p in texto.replace(",", "\t").split() if p.strip()]
        if len(partes) != 2:
            continue
        pares.append((partes[0], partes[1]))
    return pares


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evalua nombres x pares de apellidos (producto cartesiano)."
    )
    parser.add_argument(
        "--nombres",
        type=Path,
        default=DATA_RAW / "ergobaby-2024.txt",
    )
    parser.add_argument(
        "--pares",
        type=Path,
        default=DATA_INTERMEDIO / "pares_apellidos_100.txt",
    )
    parser.add_argument(
        "--por-genero",
        type=int,
        default=50,
        help="Nombres por genero (total = 2 x por_genero)",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=DATA_OUTPUTS / "ergobaby_cruzada_10k.csv",
    )
    parser.add_argument(
        "--progreso-cada",
        type=int,
        default=500,
        help="Imprimir avance cada N evaluaciones",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.nombres.is_file():
        print(f"No se encontro: {args.nombres}", file=sys.stderr)
        return 1
    if not args.pares.is_file():
        print(f"No se encontro: {args.pares}", file=sys.stderr)
        return 1
    if not DB_PATH.exists():
        print(f"No se encontro la base de datos: {DB_PATH}", file=sys.stderr)
        return 1

    nombres = nombres_balanceados(
        parsear_archivo_nombres(args.nombres), args.por_genero
    )
    pares = parsear_pares(args.pares)
    if not nombres or not pares:
        print("Nombres o pares vacios.", file=sys.stderr)
        return 1

    total = len(nombres) * len(pares)
    filas: list[dict[str, str | float | None]] = []
    inicio = time.perf_counter()

    with sqlite3.connect(DB_PATH) as conn:
        lexico = obtener_lexico(conn)
        cache_apellidos: dict[str, str] = {}

        def ipa_apellido(texto: str) -> str:
            if texto not in cache_apellidos:
                cache_apellidos[texto], _ = resolver_fonetica(
                    conn, texto, None, es_nombre=False
                )
            return cache_apellidos[texto]

        cache_nombres: dict[tuple[str, str], str] = {}

        def ipa_nombre(nombre: str, genero: str) -> str:
            clave = (nombre, genero)
            if clave not in cache_nombres:
                cache_nombres[clave], _ = resolver_fonetica(
                    conn, nombre, genero, es_nombre=True
                )
            return cache_nombres[clave]

        hechas = 0
        for apellido1, apellido2 in pares:
            ipa_ap1 = ipa_apellido(apellido1)
            ipa_ap2 = ipa_apellido(apellido2)
            for nombre, genero in nombres:
                ipa_nom = ipa_nombre(nombre, genero)
                resultado = evaluar_combinacion(
                    nombre,
                    apellido1,
                    apellido2,
                    (ipa_nom, ipa_ap1, ipa_ap2),
                    lexico=lexico,
                )
                fila: dict[str, str | float | None] = {
                    "nombre": nombre,
                    "genero": genero,
                    "apellido1": apellido1,
                    "apellido2": apellido2,
                    "fonetica_nombre": resultado.piezas[0],
                }
                fila.update(fila_modo(resultado.corto, "corto"))
                fila.update(fila_modo(resultado.completo, "completo"))
                filas.append(fila)
                hechas += 1
                if args.progreso_cada and hechas % args.progreso_cada == 0:
                    elapsed = time.perf_counter() - inicio
                    print(
                        f"  {hechas}/{total} ({100 * hechas / total:.0f}%) "
                        f"- {elapsed:.0f}s",
                        flush=True,
                    )

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=campos_csv(), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filas)

    elapsed = time.perf_counter() - inicio
    print(
        f"Evaluadas {len(filas)} combinaciones "
        f"({len(nombres)} nombres x {len(pares)} pares) -> {args.salida} "
        f"en {elapsed:.0f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
