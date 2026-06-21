#!/usr/bin/env python3
"""Genera pares T2/T3 del pilot desde pilot_samples.json (sin etiquetar)."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sqlite3
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_DB, DATA_INTERMEDIO, setup_lib

setup_lib()

from evaluar_combinacion import resolver_fonetica
from fonetica_scoring import evaluar_combinacion, extraer_features, obtener_lexico

DEFAULT_SAMPLES = DATA_INTERMEDIO / "pilot_samples.json"
DEFAULT_OUTPUT = DATA_INTERMEDIO / "pilot_pares.csv"

UMBRAL_DIFICIL = 15.0
AP2_DUMMY = "A"
ESTRATEGIAS = ("aleatorio", "dificil", "contraste")
CAMPOS_CSV = (
    "tipo",
    "genero",
    "apellido1",
    "apellido2",
    "nombre_a",
    "nombre_b",
    "estrategia",
)


@dataclass(frozen=True)
class Contexto:
    tipo: str
    genero: str
    apellido1: str
    apellido2: str


@dataclass
class MetricasNombre:
    nombre: str
    score: float
    logbigram: float
    tipo_contacto: str


def cargar_samples(ruta: Path) -> dict:
    with ruta.open(encoding="utf-8") as handle:
        return json.load(handle)


def clave_par(
    ctx: Contexto, nombre_a: str, nombre_b: str
) -> tuple[str, str, str, str, str, str]:
    a, b = sorted((nombre_a, nombre_b))
    return (ctx.tipo, ctx.genero, ctx.apellido1, ctx.apellido2, a, b)


def asignar_generos_contextos(items: list, mitad: int = 10) -> list[tuple[str, str]]:
    """Primera mitad F, segunda M: (item, genero)."""
    resultado: list[tuple[str, str]] = []
    for i, item in enumerate(items):
        genero = "F" if i < mitad else "M"
        resultado.append((item, genero))
    return resultado


def metricas_contexto(
    conn: sqlite3.Connection,
    lexico,
    ctx: Contexto,
    nombres: list[str],
) -> list[MetricasNombre]:
    ipa_ap1, _ = resolver_fonetica(conn, ctx.apellido1, None, es_nombre=False)
    if ctx.tipo == "T3":
        ipa_ap2, _ = resolver_fonetica(conn, ctx.apellido2, None, es_nombre=False)
    else:
        ipa_ap2, _ = resolver_fonetica(conn, AP2_DUMMY, None, es_nombre=False)

    filas: list[MetricasNombre] = []
    for nombre in nombres:
        ipa_n, _ = resolver_fonetica(conn, nombre, ctx.genero, es_nombre=True)
        ipa_piezas = (ipa_n, ipa_ap1, ipa_ap2)
        resultado = evaluar_combinacion(nombre, ctx.apellido1, ctx.apellido2 or AP2_DUMMY, ipa_piezas, lexico)
        score = (
            resultado.corto.nota_final
            if ctx.tipo == "T2"
            else resultado.completo.nota_final
        )
        feat = extraer_features(
            nombre,
            ctx.apellido1,
            ctx.apellido2 or AP2_DUMMY,
            ipa_piezas,
            ctx.genero,
            lexico=lexico,
            conn=conn,
        )
        filas.append(
            MetricasNombre(
                nombre=nombre,
                score=score,
                logbigram=feat.logbigram_union,
                tipo_contacto=feat.tipo_contacto,
            )
        )
    return filas


def pares_aleatorios(
    rng: random.Random,
    metricas: list[MetricasNombre],
    cantidad: int,
    usados: set[tuple[str, str, str, str, str, str]],
    ctx: Contexto,
) -> list[tuple[str, str, str]]:
    nombres = [m.nombre for m in metricas]
    elegidos: list[tuple[str, str, str]] = []
    intentos = 0
    max_intentos = cantidad * 200
    while len(elegidos) < cantidad and intentos < max_intentos:
        intentos += 1
        na, nb = rng.sample(nombres, 2)
        clave = clave_par(ctx, na, nb)
        if clave in usados:
            continue
        usados.add(clave)
        elegidos.append((na, nb, "aleatorio"))
    return elegidos


def pares_dificiles(
    rng: random.Random,
    metricas: list[MetricasNombre],
    cantidad: int,
    usados: set[tuple[str, str, str, str, str, str]],
    ctx: Contexto,
) -> list[tuple[str, str, str]]:
    candidatos: list[tuple[float, str, str]] = []
    for ma, mb in combinations(metricas, 2):
        diff = abs(ma.score - mb.score)
        if diff <= UMBRAL_DIFICIL:
            candidatos.append((diff, ma.nombre, mb.nombre))

    rng.shuffle(candidatos)
    candidatos.sort(key=lambda t: t[0])

    elegidos: list[tuple[str, str, str]] = []
    for diff, na, nb in candidatos:
        if len(elegidos) >= cantidad:
            break
        clave = clave_par(ctx, na, nb)
        if clave in usados:
            continue
        usados.add(clave)
        elegidos.append((na, nb, "dificil"))

    if len(elegidos) < cantidad:
        faltan = cantidad - len(elegidos)
        elegidos.extend(
            pares_aleatorios(rng, metricas, faltan, usados, ctx)
        )
    return elegidos


def pares_contraste(
    rng: random.Random,
    metricas: list[MetricasNombre],
    cantidad: int,
    usados: set[tuple[str, str, str, str, str, str]],
    ctx: Contexto,
) -> list[tuple[str, str, str]]:
    candidatos: list[tuple[float, str, str]] = []
    for ma, mb in combinations(metricas, 2):
        if ma.tipo_contacto == mb.tipo_contacto and abs(ma.logbigram - mb.logbigram) < 0.5:
            continue
        dist = (
            (0 if ma.tipo_contacto != mb.tipo_contacto else 1)
            + abs(ma.logbigram - mb.logbigram)
        )
        candidatos.append((dist, ma.nombre, mb.nombre))

    rng.shuffle(candidatos)
    candidatos.sort(key=lambda t: t[0], reverse=True)

    elegidos: list[tuple[str, str, str]] = []
    for _, na, nb in candidatos:
        if len(elegidos) >= cantidad:
            break
        clave = clave_par(ctx, na, nb)
        if clave in usados:
            continue
        usados.add(clave)
        elegidos.append((na, nb, "contraste"))

    if len(elegidos) < cantidad:
        faltan = cantidad - len(elegidos)
        elegidos.extend(
            pares_aleatorios(rng, metricas, faltan, usados, ctx)
        )
    return elegidos


def generar_pares_contexto(
    rng: random.Random,
    conn: sqlite3.Connection,
    lexico,
    ctx: Contexto,
    nombres: list[str],
    pares_por_contexto: int,
) -> list[dict[str, str]]:
    metricas = metricas_contexto(conn, lexico, ctx, nombres)
    usados: set[tuple[str, str, str, str, str, str]] = set()

    n_dificil = pares_por_contexto * 9 // 25
    n_contraste = pares_por_contexto * 8 // 25
    n_aleatorio = pares_por_contexto - n_dificil - n_contraste

    filas: list[dict[str, str]] = []
    for na, nb, estrategia in (
        pares_dificiles(rng, metricas, n_dificil, usados, ctx)
        + pares_contraste(rng, metricas, n_contraste, usados, ctx)
        + pares_aleatorios(rng, metricas, n_aleatorio, usados, ctx)
    ):
        if rng.random() < 0.5:
            na, nb = nb, na
        filas.append(
            {
                "tipo": ctx.tipo,
                "genero": ctx.genero,
                "apellido1": ctx.apellido1,
                "apellido2": ctx.apellido2,
                "nombre_a": na,
                "nombre_b": nb,
                "estrategia": estrategia,
            }
        )

    rng.shuffle(filas)
    return filas


def construir_contextos(samples: dict) -> list[Contexto]:
    mitad_t2 = len(samples["apellidos_t2"]) // 2
    mitad_t3 = len(samples["pares_t3"]) // 2

    t2 = [
        Contexto(tipo="T2", genero=genero, apellido1=ap1, apellido2="")
        for ap1, genero in asignar_generos_contextos(samples["apellidos_t2"], mitad_t2)
    ]
    t3 = [
        Contexto(
            tipo="T3",
            genero=genero,
            apellido1=par["apellido1"],
            apellido2=par["apellido2"],
        )
        for par, genero in asignar_generos_contextos(samples["pares_t3"], mitad_t3)
    ]
    return t2 + t3


def generar_pilot(
    conn: sqlite3.Connection,
    samples: dict,
    seed: int,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    lexico = obtener_lexico(conn)
    pares_por_contexto = int(samples["plan_pilot"]["pares_nombres_por_contexto"])
    nombres_por_genero = {
        "F": list(samples["nombres_f"]),
        "M": list(samples["nombres_m"]),
    }

    todas: list[dict[str, str]] = []
    for ctx in construir_contextos(samples):
        pool = nombres_por_genero[ctx.genero]
        todas.extend(
            generar_pares_contexto(rng, conn, lexico, ctx, pool, pares_por_contexto)
        )
    return todas


def escribir_csv(ruta: Path, filas: list[dict[str, str]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        writer.writerows(filas)


def resumir(filas: list[dict[str, str]]) -> str:
    from collections import Counter

    por_tipo = Counter(f["tipo"] for f in filas)
    por_est = Counter(f["estrategia"] for f in filas)
    lineas = [
        f"Total filas: {len(filas)}",
        f"Por tipo: {dict(por_tipo)}",
        f"Por estrategia: {dict(por_est)}",
    ]
    return "\n".join(lineas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera pares T2/T3 del pilot.")
    parser.add_argument(
        "--samples",
        type=Path,
        default=DEFAULT_SAMPLES,
        help="JSON con muestras del pilot",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="CSV de salida",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria")
    args = parser.parse_args()

    if not args.samples.is_file():
        print(f"No se encontro: {args.samples}", file=sys.stderr)
        return 1
    if not DATA_DB.is_file():
        print(f"No se encontro la base de datos: {DATA_DB}", file=sys.stderr)
        return 1

    samples = cargar_samples(args.samples)
    with sqlite3.connect(DATA_DB) as conn:
        filas = generar_pilot(conn, samples, args.seed)

    escribir_csv(args.output, filas)
    print(resumir(filas))
    print(f"Escrito en {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
