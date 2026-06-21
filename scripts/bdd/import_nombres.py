#!/usr/bin/env python3
"""Crea el esquema y carga la tabla nombres desde los CSV de fuente."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "rebuild_nombres.py"
    runpy.run_path(str(script), run_name="__main__")
