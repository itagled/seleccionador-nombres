#!/usr/bin/env python3
"""Genera pares estratificados de apellidos a partir de una lista base."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_INTERMEDIO


def parsear_apellidos(ruta: Path) -> list[str]:
    apellidos: list[str] = []
    vistos: set[str] = set()
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        texto = linea.strip()
        if not texto or texto.startswith("#"):
            continue
        if texto in vistos:
            continue
        vistos.add(texto)
        apellidos.append(texto)
    return apellidos


def generar_pares(apellidos: list[str], cantidad: int) -> list[tuple[str, str]]:
    if len(apellidos) < 2:
        raise ValueError("Se necesitan al menos 2 apellidos distintos.")
    if cantidad > len(apellidos) * (len(apellidos) - 1):
        raise ValueError("No hay suficientes pares unicos posibles.")

    pares: list[tuple[str, str]] = []
    usados: set[tuple[str, str]] = set()
    total = len(apellidos)

    for indice in range(cantidad):
        apellido1 = apellidos[indice % total]
        desplazamiento = (indice * 37 + 17) % total
        if desplazamiento == 0:
            desplazamiento = 1
        apellido2 = apellidos[(indice + desplazamiento) % total]
        if apellido1 == apellido2:
            apellido2 = apellidos[(indice + desplazamiento + 1) % total]

        clave = (apellido1, apellido2)
        intento = 0
        while clave in usados or clave[0] == clave[1]:
            intento += 1
            apellido2 = apellidos[(indice + desplazamiento + intento) % total]
            clave = (apellido1, apellido2)
            if intento > total:
                apellido1 = apellidos[(indice + intento) % total]
                apellido2 = apellidos[(indice + desplazamiento + intento) % total]
                clave = (apellido1, apellido2)

        usados.add(clave)
        pares.append(clave)

    return pares


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera pares de apellidos estratificados.")
    parser.add_argument(
        "--entrada",
        type=Path,
        default=DATA_INTERMEDIO / "apellidos_hispanos_100.txt",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=DATA_INTERMEDIO / "pares_apellidos_100.txt",
    )
    parser.add_argument("--cantidad", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apellidos = parsear_apellidos(args.entrada)
    if len(apellidos) < args.cantidad // 2:
        print(
            f"Aviso: solo {len(apellidos)} apellidos en {args.entrada}",
            file=sys.stderr,
        )

    pares = generar_pares(apellidos, args.cantidad)
    lineas = [f"{a1}\t{a2}" for a1, a2 in pares]
    args.salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Generados {len(pares)} pares -> {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
