#!/usr/bin/env python3
"""Estadisticas de subcriterios en un lote evaluado."""

from __future__ import annotations

import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluacion"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_RAW, setup_lib

setup_lib()

from evaluar_combinacion import resolver_fonetica
from evaluar_lote import DB_PATH, parsear_archivo_nombres
from fonetica_scoring import PESOS, PESOS_ATRACCION_BASE, evaluar_combinacion, obtener_lexico

CRITERIOS_RESTR = ("A", "B", "C", "D", "E", "F", "G")
CRITERIOS_ATR = ("H", "I", "J", "K", "M", "N", "P", "Q")
CRITERIOS_COMPLETO_EXTRA = ("O",)


def _nota(modo, letra: str) -> float | None:
    val = getattr(modo, f"nota_{letra}", None)
    return None if val is None else float(val)


def main() -> int:
    archivo = DATA_RAW / "ergobaby-2024.txt"
    ap1, ap2 = "Tagle", "Díaz"
    nombres = parsear_archivo_nombres(archivo)

    corto: dict[str, list[float]] = {}
    completo: dict[str, list[float]] = {}

    with sqlite3.connect(DB_PATH) as conn:
        lexico = obtener_lexico(conn)
        ipa_ap1, _ = resolver_fonetica(conn, ap1, None, es_nombre=False)
        ipa_ap2, _ = resolver_fonetica(conn, ap2, None, es_nombre=False)
        for nombre, genero in nombres:
            ipa_nombre, _ = resolver_fonetica(conn, nombre, genero, es_nombre=True)
            r = evaluar_combinacion(
                nombre, ap1, ap2, (ipa_nombre, ipa_ap1, ipa_ap2), lexico=lexico
            )
            for letra in CRITERIOS_RESTR + CRITERIOS_ATR:
                corto.setdefault(letra, []).append(_nota(r.corto, letra))
                completo.setdefault(letra, []).append(_nota(r.completo, letra))
            completo.setdefault("O", []).append(_nota(r.completo, "O"))

    def peso(modo: str, letra: str) -> float:
        if letra in PESOS:
            return PESOS[letra]
        base = PESOS_ATRACCION_BASE.get(letra, 0.0)
        if letra == "O" and modo == "completo":
            # O comparte peso con J/N/Q en modo completo (rebalanceo interno)
            return base or (1 / 30)
        return base

    for modo_nombre, datos in (("CORTO", corto), ("COMPLETO", completo)):
        print(f"\n{'=' * 72}")
        print(f"  MODO {modo_nombre}  (n={len(nombres)})")
        print(f"{'=' * 72}")
        print(
            f"{'Crit':>4}  {'media':>6} {'std':>5} {'min':>5} {'max':>5} "
            f"{'%100':>5} {'%<=50':>6}  peso  var×peso"
        )
        filas = []
        for letra in CRITERIOS_RESTR + CRITERIOS_ATR + (
            CRITERIOS_COMPLETO_EXTRA if modo_nombre == "COMPLETO" else ()
        ):
            vals = [v for v in datos[letra] if v is not None]
            if not vals:
                continue
            media = statistics.mean(vals)
            std = statistics.stdev(vals) if len(vals) > 1 else 0.0
            pct100 = 100 * sum(1 for v in vals if v >= 99.99) / len(vals)
            pct50 = 100 * sum(1 for v in vals if v <= 50.0) / len(vals)
            p = peso(modo_nombre.lower(), letra)
            filas.append((std * p, letra, media, std, min(vals), max(vals), pct100, pct50, p))

        filas.sort(reverse=True)
        for _, letra, media, std, vmin, vmax, pct100, pct50, p in filas:
            print(
                f"  {letra:>4}  {media:6.1f} {std:5.1f} {vmin:5.1f} {vmax:5.1f} "
                f"{pct100:5.0f}% {pct50:6.0f}%  {p:5.3f}  {std * p:5.2f}"
            )

        siempre100 = [
            letra
            for letra in CRITERIOS_RESTR + CRITERIOS_ATR
            + (CRITERIOS_COMPLETO_EXTRA if modo_nombre == "COMPLETO" else ())
            if all(v >= 99.99 for v in datos.get(letra, []) if v is not None)
        ]
        print()
        if siempre100:
            print(f"  Siempre 100: {', '.join(siempre100)}")
        else:
            print("  Ningun criterio esta siempre en 100.")

        casi_fijos = [
            (letra, statistics.stdev([v for v in datos[letra] if v is not None]))
            for letra in CRITERIOS_RESTR + CRITERIOS_ATR
            + (CRITERIOS_COMPLETO_EXTRA if modo_nombre == "COMPLETO" else ())
            if letra in datos and len([v for v in datos[letra] if v is not None]) > 1
        ]
        casi_fijos.sort(key=lambda x: x[1])
        print(
            "  Casi sin variacion (std<2): "
            + ", ".join(f"{l}({s:.1f})" for l, s in casi_fijos if s < 2)
            or "ninguno"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
