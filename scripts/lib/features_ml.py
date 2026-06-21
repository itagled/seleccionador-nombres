"""Vector de features ML para ranker (numéricas + one-hot tipo_contacto)."""

from __future__ import annotations

from fonetica_scoring import FeaturesEvaluacion

# Referencia omitida en one-hot: CV
TIPOS_CONTACTO = ("CV", "VC", "VV_same", "VV_dist", "CC_legal", "CC_illegal")
TIPOS_CONTACTO_ONEHOT = tuple(t for t in TIPOS_CONTACTO if t != "CV")

CAMPOS_NUMERICOS = (
    "logbigram_union",
    "n_sil_nombre",
    "n_sil_ap1",
    "n_sil_ap2",
    "sonoridad_nombre",
    "eco_vocal_union",
    "rima_completa_ap1",
    "rima_vocalica_ap1",
    "rima_completa_ap2",
    "rima_vocalica_ap2",
    "log_familiaridad",
    "prop_reciente",
)


def columna_onehot(tipo: str) -> str:
    return f"tc_{tipo}"


def columnas_features_ml() -> list[str]:
    return list(CAMPOS_NUMERICOS) + [columna_onehot(t) for t in TIPOS_CONTACTO_ONEHOT]


def onehot_tipo_contacto(tipo: str) -> dict[str, int]:
    if tipo not in TIPOS_CONTACTO:
        tipo = "CV"
    return {columna_onehot(t): int(tipo == t) for t in TIPOS_CONTACTO_ONEHOT}


def fila_features_ml(
    feat: FeaturesEvaluacion,
    *,
    genero: str | None = None,
    ipa_nombre: str | None = None,
    ipa_ap1: str | None = None,
    ipa_ap2: str | None = None,
) -> dict[str, str | int | float]:
    """Fila plana para CSV: metadatos + numéricas + one-hot (ref=CV)."""
    base = feat.to_dict()
    fila: dict[str, str | int | float] = {
        "nombre": base["nombre"],
        "apellido1": base["apellido1"],
        "apellido2": base["apellido2"],
    }
    if genero is not None:
        fila["genero"] = genero
    if ipa_nombre is not None:
        fila["ipa_nombre"] = ipa_nombre
    if ipa_ap1 is not None:
        fila["ipa_ap1"] = ipa_ap1
    if ipa_ap2 is not None:
        fila["ipa_ap2"] = ipa_ap2

    fila["tipo_contacto"] = str(base["tipo_contacto"])
    for campo in CAMPOS_NUMERICOS:
        fila[campo] = base[campo]
    fila.update(onehot_tipo_contacto(str(base["tipo_contacto"])))
    return fila


def campos_csv_export() -> list[str]:
    meta = ["nombre", "genero", "apellido1", "apellido2", "ipa_nombre", "ipa_ap1", "ipa_ap2"]
    return meta + ["tipo_contacto"] + columnas_features_ml()
