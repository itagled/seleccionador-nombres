#!/usr/bin/env python3
"""Compara jueces LLM (2 modelos × 2 prompts) vs humano en T2."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_INTERMEDIO, setup_lib

setup_lib()

from etiquetar_pares_llm import clave_fila, etiquetar_fila
from llm_client import LLMConfigError, cargar_env, resolver_api_key
from prompts_llm import MODELO_FLASH, MODELO_SONNET

DEFAULT_HUMANOS = DATA_INTERMEDIO / "pilot_pares_humanos_50.csv"
DEFAULT_LLM_PREVIO = DATA_INTERMEDIO / "pilot_pares_etiquetados_50.csv"
DEFAULT_OUTPUT = DATA_INTERMEDIO / "comparacion_jueces_t2.csv"

CONFIGS = (
    ("sonnet_eufonico", MODELO_SONNET, "eufonico", True),
    ("sonnet_cotidiano", MODELO_SONNET, "cotidiano", False),
    ("flash_eufonico", MODELO_FLASH, "eufonico", False),
    ("flash_cotidiano", MODELO_FLASH, "cotidiano", False),
)


def cargar_t2_humanos(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["tipo"] == "T2"]


def cargar_previo_sonnet_eufonico(ruta: Path) -> dict[tuple[str, ...], str]:
    if not ruta.is_file():
        return {}
    out: dict[tuple[str, ...], str] = {}
    with ruta.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["tipo"] != "T2":
                continue
            ganador = row.get("ganador", "")
            if ganador in ("A", "B"):
                out[clave_fila(row)] = ganador
    return out


def acuerdo(humano: str, llm: str) -> bool:
    return humano in ("A", "B") and llm in ("A", "B") and humano == llm


def etiquetar_config(
    conn: sqlite3.Connection,
    filas: list[dict[str, str]],
    *,
    model: str,
    prompt: str,
    api_key: str | None,
    sleep: float,
) -> dict[tuple[str, ...], str]:
    resultados: dict[tuple[str, ...], str] = {}
    for i, row in enumerate(filas, start=1):
        fila = etiquetar_fila(
            conn,
            row,
            model=model,
            api_key=api_key,
            dry_run=False,
            prompt_variant=prompt,
        )
        clave = clave_fila(row)
        resultados[clave] = fila["ganador"]
        estado = fila["ganador"] or "ERR"
        print(f"  [{i}/{len(filas)}] {row['nombre_a']} vs {row['nombre_b']} -> {estado}")
        if fila["error"]:
            print(f"    error: {fila['error']}")
        if sleep > 0 and i < len(filas):
            time.sleep(sleep)
    return resultados


def escribir_comparacion(
    ruta: Path,
    filas: list[dict[str, str]],
    predicciones: dict[str, dict[tuple[str, ...], str]],
) -> None:
    campos = [
        "tipo",
        "genero",
        "apellido1",
        "nombre_a",
        "nombre_b",
        "ganador_humano",
        *predicciones.keys(),
    ]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=campos)
        writer.writeheader()
        for row in filas:
            clave = clave_fila(row)
            out = {
                "tipo": row["tipo"],
                "genero": row["genero"],
                "apellido1": row["apellido1"],
                "nombre_a": row["nombre_a"],
                "nombre_b": row["nombre_b"],
                "ganador_humano": row["ganador_humano"],
            }
            for nombre, preds in predicciones.items():
                out[nombre] = preds.get(clave, "")
            writer.writerow(out)


def cargar_predicciones_output(
    ruta: Path,
    filas: list[dict[str, str]],
) -> dict[str, dict[tuple[str, ...], str]]:
    if not ruta.is_file():
        return {}
    nombres = {c[0] for c in CONFIGS}
    out: dict[str, dict[tuple[str, ...], str]] = {}
    with ruta.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            base = {
                "tipo": "T2",
                "genero": row["genero"],
                "apellido1": row["apellido1"],
                "apellido2": "",
                "nombre_a": row["nombre_a"],
                "nombre_b": row["nombre_b"],
            }
            clave = clave_fila(base)
            for name in nombres:
                if name in row and row[name] in ("A", "B"):
                    out.setdefault(name, {})[clave] = row[name]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Matriz 2×2: Sonnet/Flash × prompt eufónico/cotidiano vs humano T2."
    )
    parser.add_argument("--humanos", type=Path, default=DEFAULT_HUMANOS)
    parser.add_argument("--llm-previo", type=Path, default=DEFAULT_LLM_PREVIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument(
        "--sin-llm",
        action="store_true",
        help="Solo reportar con sonnet_eufonico previo (sin llamadas API)",
    )
    parser.add_argument(
        "--solo",
        nargs="+",
        choices=[c[0] for c in CONFIGS],
        help="Ejecutar solo estas configs (p. ej. flash_eufonico flash_cotidiano)",
    )
    args = parser.parse_args()

    cargar_env()
    if not args.humanos.is_file():
        print(f"No se encontró: {args.humanos}", file=sys.stderr)
        return 1

    filas = cargar_t2_humanos(args.humanos)
    if not filas:
        print("No hay filas T2 en humanos.", file=sys.stderr)
        return 1

    predicciones = cargar_predicciones_output(args.output, filas)
    previo = cargar_previo_sonnet_eufonico(args.llm_previo)
    if previo:
        predicciones["sonnet_eufonico"] = {
            clave_fila(r): previo[clave_fila(r)]
            for r in filas
            if clave_fila(r) in previo
        }
        print(f"Reutilizando sonnet+eufonico previo ({len(predicciones['sonnet_eufonico'])} T2)")

    if not args.sin_llm:
        try:
            resolver_api_key(args.api_key)
        except LLMConfigError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if not DATA_DB.is_file():
            print(f"No se encontró: {DATA_DB}", file=sys.stderr)
            return 1

        with sqlite3.connect(DATA_DB) as conn:
            configs_run = CONFIGS
            if args.solo:
                configs_run = [c for c in CONFIGS if c[0] in args.solo]
            for nombre, model, prompt, reutilizar in configs_run:
                if nombre in predicciones and len(predicciones[nombre]) >= len(filas):
                    print(f"\n=== {nombre} (ya en output, omitido) ===")
                    continue
                if reutilizar and nombre in predicciones:
                    continue
                print(f"\n=== {nombre} ({model}, prompt={prompt}) ===")
                predicciones[nombre] = etiquetar_config(
                    conn,
                    filas,
                    model=model,
                    prompt=prompt,
                    api_key=args.api_key,
                    sleep=args.sleep,
                )

    print("\n=== Acuerdo con humano (T2, n={}) ===".format(len(filas)))
    filas_tabla: list[tuple[str, int, int, float]] = []
    for nombre, _, _, _ in CONFIGS:
        preds = predicciones.get(nombre, {})
        hits = sum(
            1 for r in filas if acuerdo(r["ganador_humano"], preds.get(clave_fila(r), ""))
        )
        total = len(filas)
        pct = 100 * hits / total if total else 0
        filas_tabla.append((nombre, hits, total, pct))
        print(f"  {nombre:18s}  {hits}/{total}  ({pct:.0f}%)")

    escribir_comparacion(args.output, filas, predicciones)
    print(f"\nDetalle en {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
