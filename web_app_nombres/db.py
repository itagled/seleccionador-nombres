"""Conexión PostgreSQL y consultas del comparador."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def normalizar_database_url(url: str) -> str:
    """Render entrega postgres://; psycopg 3 prefiere postgresql://."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def obtener_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. "
            "En Render: vinculá la base PostgreSQL al Web Service."
        )
    return normalizar_database_url(url)


def conectar() -> psycopg.Connection:
    return psycopg.connect(obtener_database_url(), row_factory=dict_row)


def ensure_schema() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with conectar() as conn:
        conn.execute(sql)
        conn.commit()


def contar_pares() -> int:
    with conectar() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM pares").fetchone()
        return int(row["n"]) if row else 0


def obtener_siguiente_par(session_id: UUID) -> dict | None:
    """Par T2 activo aleatorio que esta sesión aún no votó."""
    with conectar() as conn:
        row = conn.execute(
            """
            SELECT p.id, p.genero, p.apellido1, p.forma_a, p.forma_b, p.estrategia
            FROM pares p
            WHERE p.activo = TRUE
              AND p.tipo = 'T2'
              AND NOT EXISTS (
                  SELECT 1 FROM votos v
                  WHERE v.par_id = p.id AND v.session_id = %(session_id)s
              )
            ORDER BY RANDOM()
            LIMIT 1
            """,
            {"session_id": session_id},
        ).fetchone()
        return dict(row) if row else None


def registrar_voto(*, par_id: int, ganador: str, session_id: UUID) -> bool:
    """Inserta voto. Devuelve False si ya existía (par_id, session_id)."""
    with conectar() as conn:
        cur = conn.execute(
            """
            INSERT INTO votos (par_id, ganador, session_id)
            VALUES (%(par_id)s, %(ganador)s, %(session_id)s)
            ON CONFLICT (par_id, session_id) DO NOTHING
            RETURNING id
            """,
            {"par_id": par_id, "ganador": ganador, "session_id": session_id},
        )
        conn.commit()
        return cur.fetchone() is not None


def progreso_sesion(session_id: UUID) -> dict[str, int]:
    with conectar() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM pares WHERE activo = TRUE AND tipo = 'T2'"
        ).fetchone()
        votados = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM votos v
            JOIN pares p ON p.id = v.par_id
            WHERE v.session_id = %(session_id)s
              AND p.tipo = 'T2'
              AND p.activo = TRUE
            """,
            {"session_id": session_id},
        ).fetchone()
        return {
            "votados": int(votados["n"]) if votados else 0,
            "total": int(total["n"]) if total else 0,
        }
