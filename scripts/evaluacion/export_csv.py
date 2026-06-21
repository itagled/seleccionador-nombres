"""Columnas y serializacion CSV para evaluaciones v2."""

from __future__ import annotations

from fonetica_scoring import ResultadoModo

CRITERIOS_RESTRICCION = tuple("ABCDEFG")
CRITERIOS_ATRACCION = tuple("HIJKMNOPQ")


def fila_modo(modo: ResultadoModo, prefijo: str) -> dict[str, float | None]:
    datos: dict[str, float | None] = {
        f"{prefijo}_nota_final": modo.nota_final,
        f"{prefijo}_restriccion": modo.nota_restriccion,
        f"{prefijo}_atraccion": modo.nota_atraccion,
    }
    for letra in CRITERIOS_RESTRICCION:
        datos[f"{prefijo}_{letra}"] = getattr(modo, f"nota_{letra}")
    for letra in CRITERIOS_ATRACCION:
        valor = getattr(modo, f"nota_{letra}", None)
        if letra == "O" and valor is None:
            datos[f"{prefijo}_{letra}"] = None
        else:
            datos[f"{prefijo}_{letra}"] = valor
    return datos


def campos_csv() -> list[str]:
    campos = ["nombre", "genero", "apellido1", "apellido2", "fonetica_nombre"]
    for prefijo in ("corto", "completo"):
        campos.extend(
            [
                f"{prefijo}_nota_final",
                f"{prefijo}_restriccion",
                f"{prefijo}_atraccion",
            ]
        )
        for letra in CRITERIOS_RESTRICCION + CRITERIOS_ATRACCION:
            campos.append(f"{prefijo}_{letra}")
    return campos
