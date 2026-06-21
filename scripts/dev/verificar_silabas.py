#!/usr/bin/env python3
"""Verifica silabificacion y fix de rima tras cambios en fonetica_scoring."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB
from fonetica_scoring import (
    _nota_rima_union,
    analizar_pieza,
    tokenizar_ipa,
)

CASOS = {
    2: ["Emma", "Ana", "Luna", "Clara", "Alba", "Mario", "Diego", "Sergio"],
    3: ["MARÍA", "SOFÍA", "LUCÍA", "ROCÍO", "Valeria", "Mateo"],
    4: ["Valentina", "Gabriela", "Maximiliano"],
    None: ["Diana"],  # ambiguo / reportar
}


def ipa_desde_db(conn: sqlite3.Connection, nombre: str) -> str | None:
    row = conn.execute(
        """
        SELECT fonetica FROM nombres
        WHERE nombre = ? AND fonetica IS NOT NULL
        ORDER BY CASE genero WHEN 'F' THEN 0 WHEN 'M' THEN 1 ELSE 2 END
        LIMIT 1
        """,
        (nombre.upper(),),
    ).fetchone()
    return row[0] if row else None


def main() -> int:
    lineas: list[str] = []
    conn = sqlite3.connect(DATA_DB)

    lineas.append("=== PASO 1: IPA es-419 (muestra) ===")
    muestra = [
        "Mario", "Diego", "Sergio", "Valeria", "Manuela", "MARÍA", "SOFÍA",
        "LUCÍA", "Valentina", "Mateo", "Emma",
    ]
    for n in muestra:
        ipa = ipa_desde_db(conn, n)
        lineas.append(f"  {n}: {ipa}")

    lineas.append("\n=== PASO 3: Silabas calculadas vs esperadas ===")
    ok = fail = skip = 0
    for esperado, nombres in CASOS.items():
        for nombre in nombres:
            ipa = ipa_desde_db(conn, nombre)
            if not ipa:
                lineas.append(f"  {nombre}: SIN IPA EN BD")
                skip += 1
                continue
            pieza = analizar_pieza(nombre, ipa)
            n_sil = len(pieza.silabas)
            sil_repr = " | ".join("".join(s) for s in pieza.silabas)
            if esperado is None:
                lineas.append(
                    f"  {nombre}: {n_sil} sil  [{sil_repr}]  (esperado: reportar)"
                )
                skip += 1
                continue
            estado = "OK" if n_sil == esperado else "FAIL"
            if n_sil == esperado:
                ok += 1
            else:
                fail += 1
            lineas.append(
                f"  [{estado}] {nombre}: IPA={ipa}  -> {n_sil} sil ({esperado})  [{sil_repr}]"
            )

    lineas.append("\n=== BUG 1: rima plena vs asonancia (apellido García) ===")
    garcia = analizar_pieza("García", "ɡˈaɾsja")
    if not garcia.ipa:
        garcia = analizar_pieza("García", "ɡaɾˈθja")  # fallback
    # fonetizar runtime si hace falta
    from phonemizer_config import fonetizar_texto

    ipa_g = fonetizar_texto("García")
    garcia = analizar_pieza("García", ipa_g)
    casos_rima = ["Valentina", "Sofía", "Ana", "Clara", "Mario"]
    for nom in casos_rima:
        ipa = ipa_desde_db(conn, nom if nom != "Sofía" else "SOFÍA")
        if not ipa:
            continue
        pieza = analizar_pieza(nom, ipa)
        b = _nota_rima_union(pieza, garcia)
        ult = "".join(pieza.silabas[-1])
        pri = "".join(garcia.silabas[0])
        lineas.append(
            f"  {nom}|García  ult=[{ult}] pri=[{pri}]  B={b}  "
            f"({'rima plena' if b == 0 else 'asonancia' if b == 40 else 'otro'})"
        )

    conn.close()
    lineas.append(f"\nResumen silabas: {ok} OK, {fail} FAIL, {skip} sin criterio")
    texto = "\n".join(lineas) + "\n"
    out = Path(__file__).resolve().parents[2] / "data" / "outputs" / "_verif_silabas.txt"
    out.write_text(texto, encoding="utf-8")
    print(texto)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
