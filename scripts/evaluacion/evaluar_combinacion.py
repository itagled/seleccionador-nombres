#!/usr/bin/env python3
"""Evalua eufonia fonetica v2: modos corto y completo, capas restriccion y atraccion."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_OUTPUTS, setup_lib

setup_lib()

from fonetica_scoring import (
    PESO_ATRACCION_CAPA,
    PESO_RESTRICCION_CAPA,
    PESOS,
    ResultadoEvaluacion,
    ResultadoModo,
    evaluar_combinacion,
    obtener_lexico,
)
from phonemizer_config import fonetizar_texto, preparar_nombre_para_fonetica

DB_PATH = DATA_DB


def buscar_fonetica_nombre(
    conn: sqlite3.Connection, nombre: str, genero: str | None
) -> str | None:
    nombre_db = nombre.strip().upper()
    if genero:
        row = conn.execute(
            "SELECT fonetica FROM nombres WHERE nombre = ? AND genero = ? AND fonetica IS NOT NULL LIMIT 1",
            (nombre_db, genero.upper()),
        ).fetchone()
        if row:
            return row[0]
    row = conn.execute(
        """
        SELECT fonetica FROM nombres
        WHERE nombre = ? AND fonetica IS NOT NULL
        ORDER BY CASE genero WHEN 'M' THEN 0 WHEN 'F' THEN 1 ELSE 2 END
        LIMIT 1
        """,
        (nombre_db,),
    ).fetchone()
    return row[0] if row else None


def resolver_fonetica(
    conn: sqlite3.Connection,
    texto: str,
    genero: str | None,
    es_nombre: bool,
) -> tuple[str, str]:
    if es_nombre:
        ipa_db = buscar_fonetica_nombre(conn, texto, genero)
        if ipa_db:
            return ipa_db, "base de datos"
    ipa = fonetizar_texto(preparar_nombre_para_fonetica(texto))
    return ipa, "espeak (runtime)"


def _lineas_modo(etiqueta: str, modo: ResultadoModo) -> list[str]:
    lineas = [
        f"--- Modo {etiqueta} ---",
        "",
        "  Restriccion (A-G):",
        f"    A  Fonotactica union   : {modo.nota_A:5.1f}  (peso {PESOS['A']*100:.0f}%)",
        f"    B  Anti-rima           : {modo.nota_B:5.1f}  (peso {PESOS['B']*100:.0f}%)",
        f"    C  Anti-repeticion     : {modo.nota_C:5.1f}  (peso {PESOS['C']*100:.0f}%)",
        f"    D  Anti-clusters       : {modo.nota_D:5.1f}  (peso {PESOS['D']*100:.0f}%)",
        f"    E  Anti-ritmo          : {modo.nota_E:5.1f}  (peso {PESOS['E']*100:.0f}%)",
        f"    F  Behaghel            : {modo.nota_F:5.1f}  (peso {PESOS['F']*100:.0f}%)",
        f"    G  Sandhi              : {modo.nota_G:5.1f}  (peso {PESOS['G']*100:.0f}%)",
        f"    => nota_restriccion    : {modo.nota_restriccion:5.1f}",
        "",
        "  Atraccion (H-Q):",
        f"    H  Sonoridad           : {modo.nota_H:5.1f}",
        f"    I  Balance CV          : {modo.nota_I:5.1f}",
        f"    J  Perfil silabico     : {modo.nota_J:5.1f}",
        f"    K  Fluidez fonotactica : {modo.nota_K:5.1f}",
        f"    M  Ritmo prototipico   : {modo.nota_M:5.1f}",
        f"    N  Agrupacion prosodica: {modo.nota_N:5.1f}",
    ]
    if modo.nota_O is not None:
        lineas.append(f"    O  Compacidad frase    : {modo.nota_O:5.1f}")
    lineas.extend(
        [
            f"    P  Curva sonoridad     : {modo.nota_P:5.1f}",
            f"    Q  Suavidad union      : {modo.nota_Q:5.1f}",
            f"    => nota_atraccion      : {modo.nota_atraccion:5.1f}",
            "",
            f"  NOTA FINAL ({etiqueta}): {modo.nota_final:.1f} / 100",
            f"    ({PESO_RESTRICCION_CAPA*100:.0f}% restriccion + {PESO_ATRACCION_CAPA*100:.0f}% atraccion)",
            "",
        ]
    )
    return lineas


def formatear_resultado(resultado: ResultadoEvaluacion, fuentes: tuple[str, str, str]) -> str:
    lineas = [
        f"Combinacion: {resultado.nombre} {resultado.apellido1} {resultado.apellido2}",
        "",
        "Fonetica (IPA):",
        f"  nombre    ({fuentes[0]}): {resultado.piezas[0]}",
        f"  apellido1 ({fuentes[1]}): {resultado.piezas[1]}",
        f"  apellido2 ({fuentes[2]}): {resultado.piezas[2]}",
        "",
        "Union evaluada (A,B,C,D,G,K,Q): nombre|apellido1",
        "",
    ]
    lineas.extend(_lineas_modo("corto (nombre + apellido1)", resultado.corto))
    lineas.extend(_lineas_modo("completo (nombre + apellido1 + apellido2)", resultado.completo))
    return "\n".join(lineas)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evalua eufonia fonetica v2 (modos corto y completo)."
    )
    parser.add_argument("--nombre", required=True, help="Nombre de pila")
    parser.add_argument("--apellido1", required=True, help="Primer apellido")
    parser.add_argument("--apellido2", required=True, help="Segundo apellido")
    parser.add_argument(
        "--genero",
        choices=("M", "F"),
        help="Genero del nombre (M/F) para buscar fonetica en la base de datos",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        help="Archivo UTF-8 de salida (util en consolas Windows)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not DB_PATH.exists():
        print(f"No se encontro la base de datos: {DB_PATH}", file=sys.stderr)
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        lexico = obtener_lexico(conn)
        ipa_nombre, fuente_n = resolver_fonetica(conn, args.nombre, args.genero, es_nombre=True)
        ipa_ap1, fuente_a1 = resolver_fonetica(conn, args.apellido1, None, es_nombre=False)
        ipa_ap2, fuente_a2 = resolver_fonetica(conn, args.apellido2, None, es_nombre=False)

    resultado = evaluar_combinacion(
        args.nombre.strip(),
        args.apellido1.strip(),
        args.apellido2.strip(),
        (ipa_nombre, ipa_ap1, ipa_ap2),
        lexico=lexico,
    )
    texto = formatear_resultado(resultado, (fuente_n, fuente_a1, fuente_a2))

    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto + "\n", encoding="utf-8")
        print(f"Resultado guardado en {args.salida}")
    else:
        try:
            print(texto)
        except UnicodeEncodeError:
            fallback = DATA_OUTPUTS / "ultima_evaluacion.txt"
            fallback.write_text(texto + "\n", encoding="utf-8")
            print(
                "La consola no muestra bien IPA. Resultado guardado en "
                f"{fallback}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
