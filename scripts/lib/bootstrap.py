"""Rutas del proyecto e import de modulos en scripts/lib/."""

from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = LIB_DIR.parent
ROOT = SCRIPTS_DIR.parent

DATA_DIR = ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_INTERMEDIO = DATA_DIR / "intermedio"
DATA_OUTPUTS = DATA_DIR / "outputs"
DATA_DB = DATA_DIR / "db" / "nombres.db"


def setup_lib() -> Path:
    lib = str(LIB_DIR)
    if lib not in sys.path:
        sys.path.insert(0, lib)
    return ROOT
