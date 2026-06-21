#!/usr/bin/env python3
"""Tres analisis decisivos sobre ergobaby_cruzada_10k.csv."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from bootstrap import DATA_OUTPUTS

CSV_PATH = DATA_OUTPUTS / "ergobaby_cruzada_10k.csv"
OUT_PATH = DATA_OUTPUTS / "ergobaby_cruzada_analisis.txt"

Y_COL = "corto_nota_final"
SUBCRITERIOS = [f"corto_{c}" for c in "ABCDEFGHIJKMNOPQ"]


def _par_key(df: pd.DataFrame) -> pd.Series:
    return df["apellido1"] + "|" + df["apellido2"]


def descomposicion_varianza(df: pd.DataFrame, etiqueta: str, lineas: list[str]) -> None:
    y = df[Y_COL].to_numpy(dtype=float)
    n = len(y)
    grand = y.mean()
    ss_total = np.sum((y - grand) ** 2)

    medias_nombre = df.groupby("nombre", observed=True)[Y_COL].mean()
    counts_nombre = df.groupby("nombre", observed=True)[Y_COL].count()
    ss_nombre = np.sum(counts_nombre * (medias_nombre - grand) ** 2)

    medias_par = df.groupby("apellido_par", observed=True)[Y_COL].mean()
    counts_par = df.groupby("apellido_par", observed=True)[Y_COL].count()
    ss_par = np.sum(counts_par * (medias_par - grand) ** 2)

    # Modelo aditivo saturado: residual = interaccion (1 obs/celda)
    pred = (
        df["nombre"].map(medias_nombre)
        + df["apellido_par"].map(medias_par)
        - grand
    )
    ss_residual = np.sum((y - pred.to_numpy()) ** 2)

    eta_n = ss_nombre / ss_total
    eta_p = ss_par / ss_total
    eta_r = ss_residual / ss_total

    lineas.append(f"\n### Descomposicion varianza — {etiqueta}")
    lineas.append(f"  N={n:,}  SS_total={ss_total:,.1f}")
    lineas.append(f"  {'Factor':<12} {'SS':>12} {'eta2':>8} {'%':>7}")
    lineas.append(f"  {'nombre':<12} {ss_nombre:12,.1f} {eta_n:8.3f} {100*eta_n:6.1f}%")
    lineas.append(f"  {'apellido_par':<12} {ss_par:12,.1f} {eta_p:8.3f} {100*eta_p:6.1f}%")
    lineas.append(f"  {'residuo':<12} {ss_residual:12,.1f} {eta_r:8.3f} {100*eta_r:6.1f}%  (interaccion)")
    lineas.append(f"  suma eta2 = {eta_n + eta_p + eta_r:.3f}")


def _spearman(x: pd.Series, y: pd.Series) -> float:
    a = x.rank(method="average")
    b = y.rank(method="average")
    return float(a.corr(b))


def estabilidad_ranking(df: pd.DataFrame, etiqueta: str, lineas: list[str]) -> None:
    pares = sorted(df["apellido_par"].unique())
    rankings: dict[str, pd.Series] = {}
    for par in pares:
        sub = df[df["apellido_par"] == par].sort_values(Y_COL, ascending=False)
        rankings[par] = pd.Series(
            range(1, len(sub) + 1), index=sub["nombre"].values, dtype=float
        )

    coefs: list[float] = []
    n_pares = len(pares)
    for i in range(n_pares):
        for j in range(i + 1, n_pares):
            a, b = rankings[pares[i]], rankings[pares[j]]
            aligned = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
            if len(aligned) < 3:
                continue
            rho = _spearman(aligned["a"], aligned["b"])
            if not np.isnan(rho):
                coefs.append(float(rho))

    arr = np.array(coefs)
    lineas.append(f"\n### Estabilidad ranking Spearman — {etiqueta}")
    lineas.append(f"  Pares: {n_pares}  Comparaciones (triangulo superior): {len(arr):,}")
    lineas.append(
        f"  media={arr.mean():.3f}  mediana={np.median(arr):.3f}  "
        f"p25={np.percentile(arr, 25):.3f}  p75={np.percentile(arr, 75):.3f}  "
        f"min={arr.min():.3f}  max={arr.max():.3f}"
    )
    if arr.mean() > 0.7:
        lineas.append("  >> Media > 0.7: el apellido es casi cosmético (misma lista para casi todos).")
    elif arr.mean() < 0.5:
        lineas.append("  >> Media < 0.5: personalización por apellido fuerte.")
    else:
        lineas.append("  >> Media intermedia: el apellido modifica el orden de forma moderada.")


def criterios_vs_ranking(df: pd.DataFrame, lineas: list[str]) -> None:
    cols = [c for c in SUBCRITERIOS if c in df.columns]
    # corto_O suele estar vacio
    cols = [c for c in cols if df[c].notna().sum() > 100]

    pares = sorted(df["apellido_par"].unique())
    acum: dict[str, list[float]] = {c: [] for c in cols}

    for par in pares:
        sub = df[df["apellido_par"] == par]
        if len(sub) < 5:
            continue
        for col in cols:
            s = sub[[col, Y_COL]].dropna()
            if len(s) < 5 or s[col].std() == 0:
                continue
            r = _spearman(s[col], s[Y_COL])
            if not np.isnan(r):
                acum[col].append(float(r))

    lineas.append("\n### Criterio vs ranking (Spearman dentro de par, promedio sobre pares)")
    lineas.append(f"  {'Criterio':<10} {'r_mean':>8} {'r_med':>8} {'n_pares':>8}")
    filas = []
    for col in cols:
        vals = acum[col]
        if not vals:
            continue
        letra = col.replace("corto_", "")
        filas.append((np.mean(vals), letra, np.mean(vals), np.median(vals), len(vals)))
    filas.sort(reverse=True)
    for _, letra, mean_r, med_r, n in filas:
        lineas.append(f"  {letra:<10} {mean_r:8.3f} {med_r:8.3f} {n:8d}")

    lineas.append("\n### Matriz correlacion subcriterios (Pearson, 10k filas, modo corto)")
    mat = df[cols].astype(float)
    corr = mat.corr()
    letras = [c.replace("corto_", "") for c in cols]
    header = "     " + "".join(f"{l:>5}" for l in letras)
    lineas.append(header)
    for i, li in enumerate(letras):
        fila = f"  {li:>3} "
        for j in range(len(letras)):
            fila += f"{corr.iloc[i, j]:5.2f}"
        lineas.append(fila)

    # Destacar redundancias A-K, B-G
    if "corto_A" in cols and "corto_K" in cols:
        lineas.append(f"\n  corr(A,K) = {corr.loc['corto_A', 'corto_K']:.3f}")
    if "corto_B" in cols and "corto_G" in cols:
        lineas.append(f"  corr(B,G) = {corr.loc['corto_B', 'corto_G']:.3f}")


def main() -> int:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    df["apellido_par"] = _par_key(df)

    lineas: list[str] = [
        "=" * 72,
        "ANALISIS DECISIVO: ergobaby_cruzada_10k.csv",
        f"Variable dependiente: {Y_COL} (es-419)",
        "=" * 72,
    ]

    for etiqueta, filtro in (
        ("TODOS", None),
        ("SOLO NIÑAS (F)", "F"),
        ("SOLO NIÑOS (M)", "M"),
    ):
        sub = df if filtro is None else df[df["genero"] == filtro]
        descomposicion_varianza(sub, etiqueta, lineas)

    lineas.append("\n" + "=" * 72)
    lineas.append("ESTABILIDAD DE RANKING ENTRE PARES")
    lineas.append("=" * 72)

    for etiqueta, filtro in (("NIÑAS (F)", "F"), ("NIÑOS (M)", "M")):
        estabilidad_ranking(df[df["genero"] == filtro], etiqueta, lineas)

    lineas.append("\n" + "=" * 72)
    lineas.append("CRITERIOS QUE MUEVEN EL RANKING (apellido fijo, varian nombres)")
    lineas.append("=" * 72)
    criterios_vs_ranking(df, lineas)

    texto = "\n".join(lineas) + "\n"
    OUT_PATH.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Guardado en {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
