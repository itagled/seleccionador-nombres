"""Configura espeak-ng para phonemizer."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from phonemizer.backend.espeak.wrapper import EspeakWrapper

ROOT = Path(__file__).resolve().parents[2]
VENDOR_ESPEAK = ROOT / "vendor" / "espeak-ng" / "eSpeak NG"
ESPEAK_MSI_URL = (
    "https://github.com/espeak-ng/espeak-ng/releases/download/1.50/"
    "espeak-ng-20191129-b702b03-x64.msi"
)

# Dialecto espeak-ng para fonetizacion.
# - "es"     : espanol peninsular (z/c como /θ/, ej. Gonzalo -> gonθalo)
# - "es-419" : espanol latinoamericano (z/c como /s/ en muchas regiones)
# Mantener un solo valor en todo el proyecto; cambiarlo obliga a recalcular fonetica.
FONETICA_LANGUAGE = "es-419"


def _rutas_espeak_instalacion() -> list[Path]:
    return [
        VENDOR_ESPEAK,
        Path(r"C:\Program Files\eSpeak NG"),
        Path(r"C:\Program Files (x86)\eSpeak NG"),
    ]


def asegurar_espeak_local() -> Path:
    dll = VENDOR_ESPEAK / "libespeak-ng.dll"
    if dll.is_file():
        return VENDOR_ESPEAK

    VENDOR_ESPEAK.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        msi = Path(tmp) / "espeak-ng-x64.msi"
        print("Descargando espeak-ng...")
        urllib.request.urlretrieve(ESPEAK_MSI_URL, msi)
        print("Extrayendo espeak-ng en vendor/...")
        subprocess.run(
            [
                "msiexec",
                "/a",
                str(msi),
                f"TARGETDIR={VENDOR_ESPEAK.parent}",
                "/qn",
            ],
            check=True,
        )

    if not dll.is_file():
        raise RuntimeError(f"No se pudo extraer espeak-ng en {VENDOR_ESPEAK}")

    return VENDOR_ESPEAK


def configurar_espeak() -> Path:
    if biblioteca := os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        EspeakWrapper.set_library(biblioteca)
        return Path(biblioteca).parent

    base: Path | None = None
    for candidato in _rutas_espeak_instalacion():
        dll = candidato / "libespeak-ng.dll"
        if dll.is_file():
            base = candidato
            break

    if base is None and platform.system() == "Windows":
        base = asegurar_espeak_local()

    if base is None:
        raise RuntimeError(
            "espeak-ng no esta instalado. En Windows ejecuta:\n"
            "  python scripts/setup/setup_espeak.py"
        )

    dll = base / "libespeak-ng.dll"
    exe = base / "espeak-ng.exe"
    data = base / "espeak-ng-data"

    os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = str(dll)
    os.environ["PHONEMIZER_ESPEAK_PATH"] = str(exe)
    if data.is_dir():
        os.environ["ESPEAK_DATA_PATH"] = str(data)

    EspeakWrapper.set_library(str(dll))
    return base


def fonetizar_texto(texto: str, language: str | None = None) -> str:
    from phonemizer import phonemize

    configurar_espeak()
    idioma = language or FONETICA_LANGUAGE
    resultado = phonemize(
        texto,
        language=idioma,
        backend="espeak",
        with_stress=True,
        strip=True,
        njobs=1,
    )
    return str(resultado).strip()


def preparar_nombre_para_fonetica(nombre: str) -> str:
    return nombre.strip().title()


def fonetizar_nombres(nombres: list[str], language: str | None = None) -> list[str]:
    from phonemizer import phonemize

    if not nombres:
        return []

    configurar_espeak()
    idioma = language or FONETICA_LANGUAGE
    textos = [preparar_nombre_para_fonetica(nombre) for nombre in nombres]
    resultado = phonemize(
        textos,
        language=idioma,
        backend="espeak",
        with_stress=True,
        strip=True,
        njobs=1,
    )
    if isinstance(resultado, list):
        return [str(item).strip() for item in resultado]
    return [linea.strip() for linea in str(resultado).splitlines()]
