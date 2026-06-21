"""Prevalencia y familiaridad de nombres desde guaguas (Chile 1920-2021)."""

from __future__ import annotations

import csv
import math
import sqlite3
from collections import defaultdict

from bootstrap import DATA_DB, DATA_RAW
from nombres_sources import extraer_tokens, normalizar_nombre

GUAGUAS_CSV = DATA_RAW / "guaguas.csv"

TAU = 30
ANIO_REF = 2021
EPS = 1e-6
ANIO_RECIENTE_INICIO = 2010

SCHEMA_FAMILIARIDAD = """
CREATE TABLE IF NOT EXISTS familiaridad (
    nombre_id          INTEGER PRIMARY KEY REFERENCES nombres (id) ON DELETE CASCADE,
    prevalencia        REAL NOT NULL DEFAULT 0,
    log_familiaridad   REAL NOT NULL,
    prop_reciente      REAL
);
CREATE INDEX IF NOT EXISTS idx_familiaridad_log ON familiaridad (log_familiaridad);
"""


def log_familiaridad_de_prevalencia(prevalencia: float) -> float:
    return math.log(EPS + prevalencia)


def calcular_familiaridad_guaguas(
    ruta_csv: str | None = None,
) -> dict[tuple[str, str], dict[str, float]]:
    """Agrega prevalencia ponderada por (token, genero) desde guaguas.csv."""
    path = GUAGUAS_CSV if ruta_csv is None else ruta_csv
    prevalencia: dict[tuple[str, str], float] = defaultdict(float)
    reciente_sum: dict[tuple[str, str], float] = defaultdict(float)
    reciente_count: dict[tuple[str, str], int] = defaultdict(int)

    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                anio = int(float(row["anio"]))
                proporcion = float(row["proporcion"])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isnan(proporcion):
                continue

            sexo = row.get("sexo", "").strip()
            if sexo not in {"M", "F"}:
                continue

            peso = math.exp(-(ANIO_REF - anio) / TAU)
            contrib = peso * proporcion
            for token in extraer_tokens(row.get("nombre", "")):
                clave = (normalizar_nombre(token), sexo)
                if not clave[0]:
                    continue
                prevalencia[clave] += contrib
                if ANIO_RECIENTE_INICIO <= anio <= ANIO_REF:
                    reciente_sum[clave] += proporcion
                    reciente_count[clave] += 1

    resultado: dict[tuple[str, str], dict[str, float]] = {}
    for clave, prev in prevalencia.items():
        cuenta = reciente_count.get(clave, 0)
        prop_rec = reciente_sum[clave] / cuenta if cuenta else 0.0
        resultado[clave] = {
            "prevalencia": prev,
            "log_familiaridad": log_familiaridad_de_prevalencia(prev),
            "prop_reciente": prop_rec,
        }
    return resultado


def aplicar_esquema_familiaridad(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_FAMILIARIDAD)


def poblar_tabla_familiaridad(
    conn: sqlite3.Connection,
    stats: dict[tuple[str, str], dict[str, float]] | None = None,
) -> int:
    """Rellena familiaridad para todos los nombres.id (idempotente)."""
    if stats is None:
        stats = calcular_familiaridad_guaguas()

    aplicar_esquema_familiaridad(conn)
    conn.execute("DELETE FROM familiaridad")

    filas = conn.execute("SELECT id, nombre, genero FROM nombres ORDER BY id").fetchall()
    datos: list[tuple[int, float, float, float | None]] = []
    for nombre_id, nombre, genero in filas:
        stat = stats.get((nombre, genero))
        if stat:
            datos.append(
                (
                    nombre_id,
                    stat["prevalencia"],
                    stat["log_familiaridad"],
                    stat["prop_reciente"],
                )
            )
        else:
            datos.append((nombre_id, 0.0, log_familiaridad_de_prevalencia(0.0), 0.0))

    conn.executemany(
        """
        INSERT INTO familiaridad (nombre_id, prevalencia, log_familiaridad, prop_reciente)
        VALUES (?, ?, ?, ?)
        """,
        datos,
    )
    return len(datos)


def familiaridad_de(
    nombre: str,
    genero: str,
    conn: sqlite3.Connection | None = None,
) -> tuple[float, float, float]:
    """Lookup (prevalencia, log_familiaridad, prop_reciente) para nombre/género."""
    nombre_db = normalizar_nombre(nombre)
    genero_db = genero.strip().upper()
    cerrar = False
    if conn is None:
        conn = sqlite3.connect(DATA_DB)
        cerrar = True
    try:
        fila = conn.execute(
            """
            SELECT f.prevalencia, f.log_familiaridad, f.prop_reciente
            FROM familiaridad f
            JOIN nombres n ON n.id = f.nombre_id
            WHERE n.nombre = ? AND n.genero = ?
            LIMIT 1
            """,
            (nombre_db, genero_db),
        ).fetchone()
        if fila is None:
            return 0.0, log_familiaridad_de_prevalencia(0.0), 0.0
        prop = fila[2]
        return float(fila[0]), float(fila[1]), float(prop) if prop is not None else 0.0
    finally:
        if cerrar:
            conn.close()
