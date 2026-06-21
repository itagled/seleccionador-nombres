#!/usr/bin/env python3
"""Resumen estadistico de evaluacion cruzada ergobaby x pares de apellidos."""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from bootstrap import DATA_OUTPUTS

CSV_PATH = DATA_OUTPUTS / "ergobaby_cruzada_10k.csv"
OUT_PATH = DATA_OUTPUTS / "ergobaby_cruzada_resumen.txt"

CRITERIOS_RESTR = tuple("ABCDEFG")
CRITERIOS_ATR = tuple("HIJKMNOPQ")


def _f(val: str | None) -> float | None:
    if val is None or val == "":
        return None
    return float(val)


def _stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {}
    vals_sorted = sorted(vals)
    n = len(vals)
    return {
        "n": n,
        "media": statistics.mean(vals),
        "mediana": statistics.median(vals),
        "std": statistics.stdev(vals) if n > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
        "p25": vals_sorted[n // 4],
        "p75": vals_sorted[(3 * n) // 4],
        "pct100": 100 * sum(1 for v in vals if v >= 99.99) / n,
        "pct50": 100 * sum(1 for v in vals if v <= 50.0) / n,
    }


def _corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else 0.0


def _fmt_stats(s: dict[str, float]) -> str:
    return (
        f"media={s['media']:.1f}  med={s['mediana']:.1f}  std={s['std']:.1f}  "
        f"min={s['min']:.1f}  max={s['max']:.1f}  "
        f"p25={s['p25']:.1f}  p75={s['p75']:.1f}  "
        f"%100={s['pct100']:.0f}%  %<=50={s['pct50']:.0f}%"
    )


def _rank_groups(
    groups: dict[str, list[float]], top: int = 10, reverse: bool = True
) -> list[tuple[str, float, float]]:
    filas = []
    for clave, vals in groups.items():
        if not vals:
            continue
        filas.append((clave, statistics.mean(vals), statistics.stdev(vals) if len(vals) > 1 else 0))
    filas.sort(key=lambda x: x[1], reverse=reverse)
    return filas[:top]


def main() -> int:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    n = len(rows)
    lineas: list[str] = []

    def w(text: str = "") -> None:
        lineas.append(text)

    w("=" * 78)
    w("RESUMEN: ergobaby_cruzada_10k.csv")
    w(f"Observaciones: {n:,}  (100 nombres x 100 pares de apellidos)")
    w("=" * 78)

    # --- Capas y nota final ---
    for modo in ("corto", "completo"):
        w()
        w(f"--- NOTA FINAL Y CAPAS ({modo.upper()}) ---")
        for col in (f"{modo}_nota_final", f"{modo}_restriccion", f"{modo}_atraccion"):
            vals = [_f(r[col]) for r in rows if _f(r[col]) is not None]
            w(f"  {col}: {_fmt_stats(_stats(vals))}")

    # --- Subcriterios ---
    for modo in ("corto", "completo"):
        w()
        w(f"--- SUBCRITERIOS ({modo.upper()}) — ordenados por std (mas discriminativo arriba) ---")
        w(f"  {'Crit':>4}  {'std':>5}  {'media':>6}  {'%100':>5}  {'%<=50':>6}  r_final")
        filas_crit: list[tuple[float, str, dict, float]] = []
        finales = [_f(r[f"{modo}_nota_final"]) for r in rows]
        for letra in CRITERIOS_RESTR + CRITERIOS_ATR:
            col = f"{modo}_{letra}"
            vals = [_f(r[col]) for r in rows if _f(r[col]) is not None]
            if not vals:
                continue
            s = _stats(vals)
            r = _corr(vals, finales[: len(vals)])
            filas_crit.append((s["std"], letra, s, r))
        filas_crit.sort(reverse=True)
        for std, letra, s, r in filas_crit:
            w(
                f"  {letra:>4}  {std:5.1f}  {s['media']:6.1f}  "
                f"{s['pct100']:5.0f}%  {s['pct50']:6.0f}%  {r:+.2f}"
            )

        casi_fijos = [letra for std, letra, s, _ in filas_crit if std < 3]
        if casi_fijos:
            w(f"  Casi sin variacion (std<3): {', '.join(casi_fijos)}")

    # --- Apellido1 ---
    w()
    w("--- APELLIDO1 (primer apellido) — media corto_nota_final ---")
    w("  Depende de union nombre|apellido1 (A,B,C,D,G,Q,J,N...)")
    por_ap1: dict[str, list[float]] = defaultdict(list)
    por_ap1_rest: dict[str, list[float]] = defaultdict(list)
    por_ap1_atr: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        a1 = r["apellido1"]
        por_ap1[a1].append(_f(r["corto_nota_final"]))
        por_ap1_rest[a1].append(_f(r["corto_restriccion"]))
        por_ap1_atr[a1].append(_f(r["corto_atraccion"]))

    w("  Top 10 apellido1 (nota final corta):")
    for clave, media, std in _rank_groups(por_ap1, 10, True):
        w(f"    {clave:20} media={media:.1f}  std={std:.1f}  n={len(por_ap1[clave])}")
    w("  Bottom 10 apellido1:")
    for clave, media, std in _rank_groups(por_ap1, 10, False):
        w(f"    {clave:20} media={media:.1f}  std={std:.1f}")

    w("  Top 10 apellido1 (restriccion):")
    for clave, media, std in _rank_groups(por_ap1_rest, 10, True):
        w(f"    {clave:20} restriccion={media:.1f}")
    w("  Bottom 10 apellido1 (mas penalizados en restriccion):")
    for clave, media, std in _rank_groups(por_ap1_rest, 10, False):
        w(f"    {clave:20} restriccion={media:.1f}")

    # --- Apellido2 ---
    w()
    w("--- APELLIDO2 (segundo apellido) — media corto_nota_final ---")
    w("  Impacto menor en nucleo; afecta E,F,M,N,O en modo completo")
    por_ap2: dict[str, list[float]] = defaultdict(list)
    por_ap2_comp: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        a2 = r["apellido2"]
        por_ap2[a2].append(_f(r["corto_nota_final"]))
        por_ap2_comp[a2].append(_f(r["completo_nota_final"]))

    w("  Top 10 apellido2 (nota final corta — poco efecto esperado):")
    for clave, media, std in _rank_groups(por_ap2, 10, True):
        w(f"    {clave:20} media={media:.1f}  std={std:.1f}")
    w("  Top 10 apellido2 (nota final COMPLETA — aqui si importa mas):")
    for clave, media, std in _rank_groups(por_ap2_comp, 10, True):
        w(f"    {clave:20} media={media:.1f}  std={std:.1f}")
    w("  Bottom 10 apellido2 (completo):")
    for clave, media, std in _rank_groups(por_ap2_comp, 10, False):
        w(f"    {clave:20} media={media:.1f}")

    # --- Pares ---
    w()
    w("--- PARES (apellido1 + apellido2) — media corto_nota_final ---")
    por_par: dict[str, list[float]] = defaultdict(list)
    por_par_rest: dict[str, list[float]] = defaultdict(list)
    por_par_atr: dict[str, list[float]] = defaultdict(list)
    por_par_comp: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        par = f"{r['apellido1']} {r['apellido2']}"
        por_par[par].append(_f(r["corto_nota_final"]))
        por_par_rest[par].append(_f(r["corto_restriccion"]))
        por_par_atr[par].append(_f(r["corto_atraccion"]))
        por_par_comp[par].append(_f(r["completo_nota_final"]))

    w("  Top 15 pares (corto):")
    for clave, media, std in _rank_groups(por_par, 15, True):
        w(f"    {clave:35} media={media:.1f}  std={std:.1f}")
    w("  Bottom 15 pares (corto):")
    for clave, media, std in _rank_groups(por_par, 15, False):
        w(f"    {clave:35} media={media:.1f}  std={std:.1f}")

    w("  Top 10 pares (restriccion):")
    for clave, media, _ in _rank_groups(por_par_rest, 10, True):
        w(f"    {clave:35} restriccion={media:.1f}")
    w("  Top 10 pares (atraccion):")
    for clave, media, _ in _rank_groups(por_par_atr, 10, True):
        w(f"    {clave:35} atraccion={media:.1f}")

    # Dispersion entre pares (estabilidad sistematica)
    w()
    w("--- ESTABILIDAD DE PARES (std de media por par sobre 100 nombres) ---")
    w("  Pares mas 'predecibles' (todos los nombres puntuan parecido):")
    std_por_par = [(par, statistics.stdev(vals), statistics.mean(vals)) for par, vals in por_par.items() if len(vals) > 1]
    std_por_par.sort(key=lambda x: x[1])
    for par, std, media in std_por_par[:8]:
        w(f"    {par:35} std={std:.1f}  media={media:.1f}")
    w("  Pares mas 'volatiles' (dependen mucho del nombre):")
    std_por_par.sort(key=lambda x: x[1], reverse=True)
    for par, std, media in std_por_par[:8]:
        w(f"    {par:35} std={std:.1f}  media={media:.1f}")

    # --- Nombres ---
    w()
    w("--- NOMBRES — media sobre 100 pares ---")
    por_nom: dict[str, list[float]] = defaultdict(list)
    por_nom_rest: dict[str, list[float]] = defaultdict(list)
    por_nom_atr: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        nom = r["nombre"]
        por_nom[nom].append(_f(r["corto_nota_final"]))
        por_nom_rest[nom].append(_f(r["corto_restriccion"]))
        por_nom_atr[nom].append(_f(r["corto_atraccion"]))

    w("  Top 15 nombres (corto):")
    for clave, media, std in _rank_groups(por_nom, 15, True):
        w(f"    {clave:20} media={media:.1f}  std={std:.1f}")
    w("  Bottom 15 nombres (corto):")
    for clave, media, std in _rank_groups(por_nom, 15, False):
        w(f"    {clave:20} media={media:.1f}  std={std:.1f}")

    w("  Mas restringidos (baja restriccion media):")
    for clave, media, _ in _rank_groups(por_nom_rest, 10, False):
        w(f"    {clave:20} restriccion={media:.1f}")
    w("  Mas atraccion:")
    for clave, media, _ in _rank_groups(por_nom_atr, 10, True):
        w(f"    {clave:20} atraccion={media:.1f}")

    # --- Restriccion vs atraccion gap ---
    w()
    w("--- BRECHA ATRACCION - RESTRICCION (corto) ---")
    brechas = []
    for r in rows:
        rest = _f(r["corto_restriccion"])
        atr = _f(r["corto_atraccion"])
        brechas.append(atr - rest)
    s = _stats(brechas)
    w(f"  atraccion - restriccion: {_fmt_stats(s)}")
    w("  Interpretacion: negativo = capa restriccion arrastra el total")

    # --- Criterios B y G por apellido1 ---
    w()
    w("--- CRITERIO B (rima/asonancia) por apellido1 ---")
    b_ap1: dict[str, list[float]] = defaultdict(list)
    g_ap1: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        b_ap1[r["apellido1"]].append(_f(r["corto_B"]))
        g_ap1[r["apellido1"]].append(_f(r["corto_G"]))
    w("  Apellido1 con B mas bajo (mas choques de rima):")
    for clave, media, _ in _rank_groups(b_ap1, 12, False):
        w(f"    {clave:20} B_media={media:.1f}")
    w("  Apellido1 con G mas bajo (sandhi):")
    for clave, media, _ in _rank_groups(g_ap1, 12, False):
        w(f"    {clave:20} G_media={media:.1f}")

    # --- Conclusiones automaticas ---
    w()
    w("=" * 78)
    w("CONCLUSIONES")
    w("=" * 78)

    corto_f = [_f(r["corto_nota_final"]) for r in rows]
    comp_f = [_f(r["completo_nota_final"]) for r in rows]
    w(f"  Rango nota final corto:    {min(corto_f):.1f} – {max(corto_f):.1f}  (std global {statistics.stdev(corto_f):.1f})")
    w(f"  Rango nota final completo: {min(comp_f):.1f} – {max(comp_f):.1f}  (std global {statistics.stdev(comp_f):.1f})")

    # find highest std criterion corto
    stds = []
    for letra in CRITERIOS_RESTR + CRITERIOS_ATR:
        col = f"corto_{letra}"
        vals = [_f(r[col]) for r in rows if _f(r[col]) is not None]
        if vals:
            stds.append((statistics.stdev(vals), letra, statistics.mean(vals)))
    stds.sort(reverse=True)
    w(f"  Criterios mas variables (corto): {', '.join(f'{l}(std={s:.1f})' for s,l,_ in stds[:5])}")
    w(f"  Criterios menos variables (corto): {', '.join(f'{l}(std={s:.1f})' for s,l,_ in stds[-5:])}")

    ap1_spread = max(statistics.mean(v) for v in por_ap1.values()) - min(statistics.mean(v) for v in por_ap1.values())
    ap2_spread_corto = max(statistics.mean(v) for v in por_ap2.values()) - min(statistics.mean(v) for v in por_ap2.values())
    ap2_spread_comp = max(statistics.mean(v) for v in por_ap2_comp.values()) - min(statistics.mean(v) for v in por_ap2_comp.values())
    par_spread = max(statistics.mean(v) for v in por_par.values()) - min(statistics.mean(v) for v in por_par.values())
    w(f"  Spread media apellido1 (corto): {ap1_spread:.1f} pts entre mejor y peor ap1")
    w(f"  Spread media apellido2 (corto): {ap2_spread_corto:.1f} pts  |  completo: {ap2_spread_comp:.1f} pts")
    w(f"  Spread media pares (corto): {par_spread:.1f} pts entre mejor y peor par")

    OUT_PATH.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Resumen -> {OUT_PATH} ({len(lineas)} lineas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
