"""Variantes de system/user prompt para etiquetado LLM pairwise (T2)."""

from __future__ import annotations

# --- Variante eufónica (prompt original) ---------------------------------

PROMPT_EUFONICO_SYSTEM = """\
Sos un evaluador de eufonía del español latinoamericano (es-419).
Comparás dos nombres de pila con un apellido (modo T2: nombre + apellido1).
Elegí cuál suena mejor al DECIR EN VOZ ALTA el nombre completo.
Ignorá popularidad, moda, ortografía, significado y preferencias personales.
Usá la transcripción IPA como guía fonética, no la grafía.
Respondé únicamente con la letra A o B, sin explicación.\
"""

# --- Variante cotidiana (frases de la vida real) -------------------------

PROMPT_COTIDIANO_SYSTEM = """\
Sos un evaluador de eufonía del español latinoamericano (es-419).
Comparás dos formas completas nombre + apellido (modo T2: un apellido).
Para decidir, usá cómo sonarían en la vida cotidiana al presentarlas en voz alta.

Ejemplos de cómo pensar la decisión (con nombres ficticios):
1. "¿Quién te cae mejor? ¿la Sofía Tagle o la Fernanda Tagle?"
2. "¿Con cuál te quedás? ¿la Luna García o la Emma García?"
3. "¿Cuál suena más natural cuando lo decís en voz alta? ¿el Mateo Tagle o el Sebastián Tagle?"
4. "Si tuvieras que presentarla así, ¿la Valentina López o la Martina López?"
5. "¿Cuál te cierra mejor al oído? ¿la Julia Díaz o la Rocío Díaz?"

En cada par real, reemplazá mentalmente las opciones A y B en frases como esas
(con artículo la/el según corresponda) y elegí la que suena mejor al oído.
Ignorá popularidad, moda, ortografía y significado.
La IPA del nombre es ayuda fonética, no la grafía.
Respondé únicamente con la letra A o B, sin explicación.\
"""

PLANTILLAS_COTIDIANO = (
    "¿Quién te cae mejor? ¿{par1} o {par2}?",
    "¿Con cuál te quedás? ¿{par1} o {par2}?",
    "¿Cuál suena más natural cuando lo decís en voz alta? ¿{par1} o {par2}?",
    "Si tuvieras que presentarla así, ¿{par1} o {par2}?",
    "¿Cuál te cierra mejor al oído? ¿{par1} o {par2}?",
)

VARIANTES_SYSTEM = {
    "eufonico": PROMPT_EUFONICO_SYSTEM,
    "cotidiano": PROMPT_COTIDIANO_SYSTEM,
}

# Compat con imports viejos
PROMPT_EUFONICO = PROMPT_EUFONICO_SYSTEM
PROMPT_COTIDIANO = PROMPT_COTIDIANO_SYSTEM
VARIANTES = VARIANTES_SYSTEM

MODELO_SONNET = "anthropic/claude-sonnet-4.6"
MODELO_FLASH = "google/gemini-3.5-flash"


def _con_articulo(genero: str, forma_completa: str) -> str:
    """'Sofía Tagle' -> 'la Sofía Tagle' (F) o 'el Mateo Tagle' (M)."""
    articulo = "la" if genero.upper() == "F" else "el"
    return f"{articulo} {forma_completa}"


def frases_cotidianas_instanciadas(genero: str, forma_a: str, forma_b: str) -> list[str]:
    par1 = _con_articulo(genero, forma_a)
    par2 = _con_articulo(genero, forma_b)
    return [tpl.format(par1=par1, par2=par2) for tpl in PLANTILLAS_COTIDIANO]


def armar_mensajes(
    *,
    prompt_variant: str,
    genero: str,
    tipo: str,
    contexto_ap: str,
    forma_a: str,
    forma_b: str,
    ipa_a: str,
    ipa_b: str,
) -> list[dict[str, str]]:
    """Arma system + user según variante eufonico | cotidiano."""
    system = VARIANTES_SYSTEM[prompt_variant]
    genero_txt = "niña" if genero.upper() == "F" else "niño"

    if prompt_variant == "cotidiano":
        frases = frases_cotidianas_instanciadas(genero, forma_a, forma_b)
        bloque_frases = "\n".join(f'{i + 1}. "{f}"' for i, f in enumerate(frases))
        user = f"""Contexto:
- Bebé: {genero_txt}
- Apellido(s): {contexto_ap}
- Modo: {tipo}

Opción A: {forma_a}
  IPA nombre: {ipa_a}

Opción B: {forma_b}
  IPA nombre: {ipa_b}

Pensá estas frases con los nombres de arriba y elegí la opción que suena mejor:
{bloque_frases}

Respondé solo A o B."""
    else:
        user = f"""Contexto:
- Bebé: {genero_txt}
- Apellido(s): {contexto_ap}
- Modo: {tipo} (eufonía al pronunciar el nombre completo)

Opción A: {forma_a}
  IPA nombre: {ipa_a}

Opción B: {forma_b}
  IPA nombre: {ipa_b}

¿Cuál suena mejor al decirlo en voz alta? Respondé solo A o B."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
