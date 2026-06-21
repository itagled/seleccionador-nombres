#!/usr/bin/env python3
"""Descarga los datos del paquete R guaguas (Chile, 1920-2021) y los exporta a CSV."""

from __future__ import annotations

import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd
import rdata

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_RAW

DATA_DIR = DATA_RAW
CRAN_URL = "https://cran.r-project.org/src/contrib/guaguas_0.3.0.tar.gz"
OUTPUT_FILES = {
    "guaguas": DATA_DIR / "guaguas.csv",
    "guaguas_frecuentes": DATA_DIR / "guaguas_frecuentes.csv",
}


def descargar_paquete(destino: Path) -> None:
    print(f"Descargando paquete desde CRAN: {CRAN_URL}")
    urllib.request.urlretrieve(CRAN_URL, destino)


def extraer_sysdata(tar_path: Path) -> Path:
    with tarfile.open(tar_path, "r:gz") as archivo:
        miembro = archivo.getmember("guaguas/R/sysdata.rda")
        archivo.extract(miembro, path=tar_path.parent)
    return tar_path.parent / "guaguas" / "R" / "sysdata.rda"


def exportar_csv(rda_path: Path) -> None:
    parsed = rdata.parser.parse_file(rda_path)
    converted = rdata.conversion.convert(parsed)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for nombre, dataframe in converted.items():
        destino = OUTPUT_FILES.get(nombre, DATA_DIR / f"{nombre}.csv")
        pd.DataFrame(dataframe).to_csv(destino, index=False)
        print(f"  {nombre}: {len(dataframe):,} filas -> {destino}")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tarball = tmp_path / "guaguas_0.3.0.tar.gz"
            descargar_paquete(tarball)
            sysdata = extraer_sysdata(tarball)
            print("Exportando datasets a CSV...")
            exportar_csv(sysdata)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Descarga completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
