#!/usr/bin/env python3
"""Etiqueta pares del pilot con un LLM vía OpenRouter (u API compatible)."""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_INTERMEDIO, setup_lib

setup_lib()

from evaluar_combinacion import resolver_fonetica
from llm_client import (
    DEFAULT_MODEL,
    LLMConfigError,
    LLMError,
    cargar_env,
    chat_completion,
    resolver_api_key,
)
# Prompts eufonico | cotidiano (frases de ejemplo): scripts/lib/prompts_llm.py
from prompts_llm import VARIANTES, armar_mensajes

DEFAULT_INPUT = DATA_INTERMEDIO / "pilot_pares.csv"
DEFAULT_OUTPUT = DATA_INTERMEDIO / "pilot_pares_etiquetados.csv"
PILOT_50_OUTPUT = DATA_INTERMEDIO / "pilot_pares_etiquetados_50.csv"

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
    "ganador",
    "fuente",
    "modelo",
    "prompt",
    "error",
)


def _imprimir(texto: str) -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((texto + "\n").encode("utf-8", errors="replace"))


def clave_fila(row: dict[str, str]) -> tuple[str, ...]:
    return (
        row["tipo"],
        row["genero"],
        row["apellido1"],
        row["apellido2"],
        row["nombre_a"],
        row["nombre_b"],
    )


def forma_completa(nombre: str, ap1: str, ap2: str) -> str:
    if ap2:
        return f"{nombre} {ap1} {ap2}"
    return f"{nombre} {ap1}"


def resolver_ipas(
    conn: sqlite3.Connection,
    row: dict[str, str],
) -> tuple[str, str, str, str]:
    genero = row["genero"]
    ap1 = row["apellido1"]
    ap2 = row["apellido2"]

    ipa_a, _ = resolver_fonetica(conn, row["nombre_a"], genero, es_nombre=True)
    ipa_b, _ = resolver_fonetica(conn, row["nombre_b"], genero, es_nombre=True)
    ipa_ap1, _ = resolver_fonetica(conn, ap1, None, es_nombre=False)
    ipa_ap2 = ""
    if ap2:
        ipa_ap2, _ = resolver_fonetica(conn, ap2, None, es_nombre=False)

    forma_a = forma_completa(row["nombre_a"], ap1, ap2)
    forma_b = forma_completa(row["nombre_b"], ap1, ap2)
    return forma_a, forma_b, ipa_a, ipa_b


def armar_prompt(
    row: dict[str, str],
    forma_a: str,
    forma_b: str,
    ipa_a: str,
    ipa_b: str,
    *,
    prompt_variant: str = "eufonico",
) -> list[dict[str, str]]:
    if row["tipo"] == "T3" and row["apellido2"]:
        contexto_ap = f"{row['apellido1']} {row['apellido2']}"
    else:
        contexto_ap = row["apellido1"]

    return armar_mensajes(
        prompt_variant=prompt_variant,
        genero=row["genero"],
        tipo=row["tipo"],
        contexto_ap=contexto_ap,
        forma_a=forma_a,
        forma_b=forma_b,
        ipa_a=ipa_a,
        ipa_b=ipa_b,
    )


def parsear_ganador(texto: str) -> str | None:
    limpio = texto.strip().upper()
    if limpio in ("A", "B"):
        return limpio
    match = re.search(r"\b([AB])\b", limpio)
    if match:
        return match.group(1)
    if limpio.startswith("A"):
        return "A"
    if limpio.startswith("B"):
        return "B"
    return None


def cargar_etiquetados(ruta: Path) -> set[tuple[str, ...]]:
    if not ruta.is_file():
        return set()
    with ruta.open(encoding="utf-8", newline="") as handle:
        return {clave_fila(row) for row in csv.DictReader(handle)}


def leer_pendientes(
    entrada: Path,
    ya_hechos: set[tuple[str, ...]],
    limite: int | None,
    estratificado: bool = False,
    solo_t2: bool = False,
) -> list[dict[str, str]]:
    with entrada.open(encoding="utf-8", newline="") as handle:
        filas = [row for row in csv.DictReader(handle) if clave_fila(row) not in ya_hechos]
    if solo_t2:
        filas = [row for row in filas if row["tipo"] == "T2"]
    if limite is None:
        return filas
    if not estratificado or limite < 2:
        return filas[:limite]

    mitad = limite // 2
    resto = limite - mitad * 2
    t2 = [row for row in filas if row["tipo"] == "T2"]
    t3 = [row for row in filas if row["tipo"] == "T3"]
    elegidos = t2[: mitad + resto] + t3[:mitad]
    if len(elegidos) < limite:
        usados = {clave_fila(row) for row in elegidos}
        for row in filas:
            if len(elegidos) >= limite:
                break
            if clave_fila(row) not in usados:
                elegidos.append(row)
                usados.add(clave_fila(row))
    return elegidos[:limite]


def escribir_encabezado(ruta: Path) -> None:
    if ruta.is_file() and ruta.stat().st_size > 0:
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=CAMPOS_SALIDA).writeheader()


def append_fila(ruta: Path, fila: dict[str, str]) -> None:
    with ruta.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=CAMPOS_SALIDA).writerow(fila)


def etiquetar_fila(
    conn: sqlite3.Connection,
    row: dict[str, str],
    *,
    model: str,
    api_key: str | None,
    dry_run: bool,
    prompt_variant: str = "eufonico",
) -> dict[str, str]:
    forma_a, forma_b, ipa_a, ipa_b = resolver_ipas(conn, row)
    messages = armar_prompt(
        row, forma_a, forma_b, ipa_a, ipa_b, prompt_variant=prompt_variant
    )

    base = {
        "tipo": row["tipo"],
        "genero": row["genero"],
        "apellido1": row["apellido1"],
        "apellido2": row["apellido2"],
        "nombre_a": row["nombre_a"],
        "nombre_b": row["nombre_b"],
        "estrategia": row.get("estrategia", ""),
        "forma_a": forma_a,
        "forma_b": forma_b,
        "ipa_a": ipa_a,
        "ipa_b": ipa_b,
        "ganador": "",
        "fuente": "",
        "modelo": "",
        "prompt": prompt_variant,
        "error": "",
    }

    if dry_run:
        _imprimir(f"--- prompt={prompt_variant} ---")
        for msg in messages:
            _imprimir(f"[{msg['role'].upper()}]\n{msg['content']}\n")
        base["ganador"] = "?"
        base["fuente"] = "dry-run"
        return base

    try:
        resp = chat_completion(messages, model=model, api_key=api_key, temperature=0.0)
        ganador = parsear_ganador(resp.content)
        if ganador is None:
            raise LLMError(f"No se pudo parsear ganador: {resp.content!r}")
        base["ganador"] = ganador
        base["fuente"] = "llm"
        base["modelo"] = resp.model
    except (LLMError, LLMConfigError) as exc:
        base["error"] = str(exc)
        base["fuente"] = "llm"
        base["modelo"] = model

    return base


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Etiqueta pares del pilot con LLM (OpenRouter por defecto)."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="ID de modelo OpenRouter")
    parser.add_argument("--api-key", default=None, help="Override de OR_KEY / OPENROUTER_API_KEY")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de filas a procesar")
    parser.add_argument(
        "--estratificado",
        action="store_true",
        help="Con --limit: mitad T2 + mitad T3 (p. ej. 25+25)",
    )
    parser.add_argument(
        "--pilot-50",
        action="store_true",
        help="Atajo: --limit 50 --estratificado --output pilot_pares_etiquetados_50.csv",
    )
    parser.add_argument(
        "--prompt",
        choices=sorted(VARIANTES),
        default="eufonico",
        help="Variante de system prompt",
    )
    parser.add_argument(
        "--solo-t2",
        action="store_true",
        help="Solo filas T2",
    )
    parser.add_argument("--resume", action="store_true", help="Omitir filas ya en --output")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar prompts sin llamar al LLM")
    parser.add_argument("--sleep", type=float, default=0.3, help="Pausa entre llamadas (s)")
    args = parser.parse_args()
    if args.pilot_50:
        args.limit = 50
        args.estratificado = True
        args.output = PILOT_50_OUTPUT

    cargar_env()
    if args.dry_run and args.limit is None:
        args.limit = 1

    if not args.input.is_file():
        print(f"No se encontró: {args.input}", file=sys.stderr)
        return 1
    if not args.dry_run and not DATA_DB.is_file():
        print(f"No se encontró la base de datos: {DATA_DB}", file=sys.stderr)
        return 1

    if not args.dry_run:
        try:
            resolver_api_key(args.api_key)
        except LLMConfigError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    ya_hechos = cargar_etiquetados(args.output) if args.resume else set()
    pendientes = leer_pendientes(
        args.input,
        ya_hechos,
        args.limit,
        estratificado=args.estratificado,
        solo_t2=args.solo_t2,
    )
    if not pendientes:
        print("Nada que procesar.")
        return 0

    if args.estratificado and args.limit:
        from collections import Counter

        mix = Counter(row["tipo"] for row in pendientes)
        print(f"Muestra estratificada: {dict(mix)}")

    escribir_encabezado(args.output)
    ok = 0
    err = 0

    with sqlite3.connect(DATA_DB) as conn:
        for i, row in enumerate(pendientes, start=1):
            fila = etiquetar_fila(
                conn,
                row,
                model=args.model,
                api_key=args.api_key,
                dry_run=args.dry_run,
                prompt_variant=args.prompt,
            )
            if not args.dry_run:
                append_fila(args.output, fila)
            if fila["ganador"] in ("A", "B"):
                ok += 1
            else:
                err += 1
            estado = fila["ganador"] or "ERR"
            print(f"[{i}/{len(pendientes)}] {row['nombre_a']} vs {row['nombre_b']} -> {estado}")
            if not args.dry_run and args.sleep > 0 and i < len(pendientes):
                time.sleep(args.sleep)

    print(f"Listo: {ok} etiquetados, {err} sin ganador.")
    if not args.dry_run:
        print(f"Escrito en {args.output}")
    return 0 if err == 0 or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
