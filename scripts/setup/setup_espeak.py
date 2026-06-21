#!/usr/bin/env python3
"""Descarga y extrae espeak-ng en vendor/ para phonemizer."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import setup_lib
from phonemizer_config import asegurar_espeak_local, configurar_espeak

setup_lib()


def main() -> int:
    base = asegurar_espeak_local()
    configurar_espeak()
    print(f"espeak-ng listo en: {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
