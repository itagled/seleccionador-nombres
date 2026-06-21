#!/usr/bin/env python3
"""Clasificación humana en terminal de la muestra pilot (mismos pares que el LLM)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_INTERMEDIO, setup_lib

setup_lib()

DEFAULT_MUESTRA = DATA_INTERMEDIO / "pilot_pares_etiquetados_50.csv"
DEFAULT_OUTPUT = DATA_INTERMEDIO / "pilot_pares_humanos_50.csv"

CAMPOS_SALIDA = (
    "tipo",
    "genero",
    "apellido1",
    "apellido2",
    "nombre_a",
    "nombre_b",
    "estrategia",
    "forma_a",
    "forma_b",
    "ipa_a",
    "ipa_b",
    "ganador_humano",
    "ganador_llm",
    "acuerdo",
    "fuente",
)

AYUDA = """Controles:
  A / B     — elegir opción (también a / b)
  i         — mostrar u ocultar IPA
  p         — pasar (sin etiquetar este par)
  q         — guardar y salir
"""


def _imprimir(texto: str = "") -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((texto + "\n").encode("utf-8", errors="replace"))


def clave_fila(row: dict[str, str]) -> tuple[str, ...]:
    return (
        row["tipo"],
        row["genero"],
        row["apellido1"],
        row.get("apellido2", ""),
        row["nombre_a"],
        row["nombre_b"],
    )


def cargar_muestra(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def cargar_progreso(ruta: Path) -> dict[tuple[str, ...], dict[str, str]]:
    if not ruta.is_file():
        return {}
    with ruta.open(encoding="utf-8", newline="") as handle:
        return {clave_fila(row): row for row in csv.DictReader(handle)}


def escribir_todo(ruta: Path, filas: list[dict[str, str]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAMPOS_SALIDA)
        writer.writeheader()
        writer.writerows(filas)


def fila_salida(
    origen: dict[str, str],
    ganador_humano: str,
) -> dict[str, str]:
    ganador_llm = origen.get("ganador", "")
    acuerdo = ""
    if ganador_humano in ("A", "B") and ganador_llm in ("A", "B"):
        acuerdo = "si" if ganador_humano == ganador_llm else "no"
    return {
        "tipo": origen["tipo"],
        "genero": origen["genero"],
        "apellido1": origen["apellido1"],
        "apellido2": origen.get("apellido2", ""),
        "nombre_a": origen["nombre_a"],
        "nombre_b": origen["nombre_b"],
        "estrategia": origen.get("estrategia", ""),
        "forma_a": origen.get("forma_a", ""),
        "forma_b": origen.get("forma_b", ""),
        "ipa_a": origen.get("ipa_a", ""),
        "ipa_b": origen.get("ipa_b", ""),
        "ganador_humano": ganador_humano,
        "ganador_llm": ganador_llm,
        "acuerdo": acuerdo,
        "fuente": "humano",
    }


def mostrar_par(
    idx: int,
    total: int,
    row: dict[str, str],
    *,
    mostrar_ipa: bool,
) -> None:
    genero = "niña" if row["genero"] == "F" else "niño"
    if row["tipo"] == "T3" and row.get("apellido2"):
        apellidos = f"{row['apellido1']} {row['apellido2']}"
    else:
        apellidos = row["apellido1"]

    _imprimir()
    _imprimir(f"=== Par {idx}/{total} · {row['tipo']} · {genero} ===")
    _imprimir(f"Apellido(s): {apellidos}")
    _imprimir()
    forma_a = row.get("forma_a") or f"{row['nombre_a']} {apellidos}".strip()
    forma_b = row.get("forma_b") or f"{row['nombre_b']} {apellidos}".strip()
    _imprimir(f"  [A] {forma_a}")
    if mostrar_ipa and row.get("ipa_a"):
        _imprimir(f"      IPA: {row['ipa_a']}")
    _imprimir(f"  [B] {forma_b}")
    if mostrar_ipa and row.get("ipa_b"):
        _imprimir(f"      IPA: {row['ipa_b']}")
    _imprimir()
    _imprimir("¿Cuál suena mejor al decirlo en voz alta?")
    _imprimir(AYUDA)


def leer_respuesta() -> str | None:
    try:
        return input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "q"


def resumir(filas: list[dict[str, str]]) -> None:
    etiquetados = [f for f in filas if f["ganador_humano"] in ("A", "B")]
    acuerdos = [f for f in etiquetados if f["acuerdo"] == "si"]
    _imprimir()
    _imprimir(f"Etiquetados por vos: {len(etiquetados)}/{len(filas)}")
    if etiquetados:
        pct = 100 * len(acuerdos) / len(etiquetados)
        _imprimir(f"Acuerdo con LLM: {len(acuerdos)}/{len(etiquetados)} ({pct:.0f}%)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clasificación humana en terminal (misma muestra que pilot LLM)."
    )
    parser.add_argument(
        "--muestra",
        type=Path,
        default=DEFAULT_MUESTRA,
        help="CSV con los 50 pares del pilot LLM",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="CSV de salida con ganador_humano",
    )
    parser.add_argument(
        "--reiniciar",
        action="store_true",
        help="Ignorar progreso previo en --output",
    )
    args = parser.parse_args()

    if not args.muestra.is_file():
        _imprimir(f"No se encontró la muestra: {args.muestra}")
        return 1

    muestra = cargar_muestra(args.muestra)
    if not muestra:
        _imprimir("La muestra está vacía.")
        return 1

    progreso = {} if args.reiniciar else cargar_progreso(args.output)
    resultados: list[dict[str, str]] = []
    pendientes: list[dict[str, str]] = []
    mostrar_ipa = False

    for row in muestra:
        clave = clave_fila(row)
        if clave in progreso and progreso[clave]["ganador_humano"] in ("A", "B"):
            resultados.append(progreso[clave])
        else:
            pendientes.append(row)

    total = len(muestra)
    ya = len(resultados)
    if ya:
        _imprimir(f"Retomando: {ya}/{total} ya etiquetados.")

    for i, row in enumerate(pendientes, start=ya + 1):
        while True:
            mostrar_par(i, total, row, mostrar_ipa=mostrar_ipa)
            resp = leer_respuesta()
            if resp in ("a", "b"):
                ganador = resp.upper()
                fila = fila_salida(row, ganador)
                resultados.append(fila)
                progreso[clave_fila(row)] = fila
                escribir_todo(args.output, _ordenar_resultados(muestra, resultados, progreso))
                break
            if resp == "i":
                mostrar_ipa = not mostrar_ipa
                continue
            if resp == "p":
                _imprimir("(pasado)")
                break
            if resp == "q":
                resumir([progreso[clave_fila(r)] for r in muestra if clave_fila(r) in progreso])
                _imprimir(f"Guardado en {args.output}")
                return 0
            _imprimir("Respuesta no válida. Usá A, B, i, p o q.")

    # Completar filas pasadas o faltantes al cerrar
    final = _ordenar_resultados(muestra, resultados, progreso)
    escribir_todo(args.output, final)
    resumir(final)
    _imprimir(f"Listo. Guardado en {args.output}")
    return 0


def _ordenar_resultados(
    muestra: list[dict[str, str]],
    resultados: list[dict[str, str]],
    progreso: dict[tuple[str, ...], dict[str, str]],
) -> list[dict[str, str]]:
    por_clave = {clave_fila(r): r for r in resultados}
    por_clave.update(progreso)
    ordenados: list[dict[str, str]] = []
    for row in muestra:
        clave = clave_fila(row)
        if clave in por_clave:
            ordenados.append(por_clave[clave])
    return ordenados


if __name__ == "__main__":
    raise SystemExit(main())
