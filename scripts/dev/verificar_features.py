#!/usr/bin/env python3
"""Verifica extraer_features() con combos de prueba."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluacion"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_OUTPUTS, setup_lib

setup_lib()

from evaluar_combinacion import resolver_fonetica
from fonetica_scoring import extraer_features, obtener_lexico

CASOS = [
    ("Luna", "F", "García", "Romero"),
    ("Carmen", "F", "García", "Romero"),
    ("David", "M", "García", "Romero"),
    ("Sofía", "F", "Tagle", "Díaz"),
    ("Ramón", "M", "Calderón", "Pinto"),
]


def main() -> int:
    lineas: list[str] = []
    with sqlite3.connect(DATA_DB) as conn:
        lexico = obtener_lexico(conn)
        for nombre, genero, ap1, ap2 in CASOS:
            ipa_n, _ = resolver_fonetica(conn, nombre, genero, es_nombre=True)
            ipa_a1, _ = resolver_fonetica(conn, ap1, None, es_nombre=False)
            ipa_a2, _ = resolver_fonetica(conn, ap2, None, es_nombre=False)
            feat = extraer_features(
                nombre, ap1, ap2, (ipa_n, ipa_a1, ipa_a2), lexico=lexico
            )
            lineas.append(f"\n{nombre} {ap1} {ap2} ({genero})")
            lineas.append(f"  IPA: {ipa_n} | {ipa_a1} | {ipa_a2}")
            for k, v in feat.to_dict().items():
                if k in ("nombre", "apellido1", "apellido2"):
                    continue
                lineas.append(f"  {k}: {v}")

    out = DATA_OUTPUTS / "_verif_features.txt"
    out.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
