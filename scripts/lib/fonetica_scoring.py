"""Puntuacion fonetica v2: modos corto/completo, capas restriccion y atraccion."""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass

from bootstrap import DATA_DB

DB_PATH = DATA_DB

VOCALES = frozenset("aeiouɪ")
VOCALES_FUERTES = frozenset("aeo")
VOCALES_DEBILES = frozenset("iuɪ")
MARCAS_ACENTO = frozenset("ˈˌ")

CLUSTERS_RAROS = frozenset(
    {
        "pt",
        "mn",
        "ps",
        "pn",
        "kn",
        "pf",
        "ts",
        "dz",
        "sr",
        "vr",
        "sch",
    }
)

ONSETS_LEGALES = frozenset(
    {
        "bl",
        "br",
        "cl",
        "cr",
        "dr",
        "fl",
        "fr",
        "gl",
        "gr",
        "pl",
        "pr",
        "tr",
        "kl",
        "kr",
        "sp",
        "st",
        "sk",
        "sm",
        "sn",
        "sf",
        "ɡl",
        "ɡr",
    }
)

PLANTILLAS_CORTO = (
    (2, 2),
    (2, 1),
    (3, 2),
    (2, 3),
    (3, 1),
    (1, 2),
)

PLANTILLAS_COMPLETO = (
    (2, 2, 2),
    (2, 2, 1),
    (3, 2, 2),
    (2, 3, 2),
    (2, 1, 2),
    (3, 2, 1),
    (1, 2, 2),
)

PESOS = {
    "A": 0.25,
    "B": 0.15,
    "C": 0.15,
    "D": 0.15,
    "E": 0.15,
    "F": 0.10,
    "G": 0.05,
}

PESOS_ATRACCION_BASE = {
    "K": 0.25,
    "M": 0.20,
    "H": 0.15,
    "P": 0.10,
    "I": 0.10,
    "O": 0.10,
    "J": 1 / 30,
    "N": 1 / 30,
    "Q": 1 / 30,
}

PESO_RESTRICCION_CAPA = 0.70
PESO_ATRACCION_CAPA = 0.30

OBSTRUYENTES_SORDOS = frozenset("ptkfsθxʃʧ")
SONORANTES = frozenset("mnlrɲʎjw")


@dataclass(frozen=True)
class PiezaFonetica:
    texto: str
    ipa: str
    tokens: tuple[str, ...]
    silabas: tuple[tuple[str, ...], ...]
    indice_acento: int | None


@dataclass(frozen=True)
class NucleoUnion:
    """Criterios que dependen solo de la union nombre|apellido1."""

    nota_A: float
    nota_B: float
    nota_C: float
    nota_D: float
    nota_G: float
    nota_K: float
    nota_Q: float
    log_bigrama_union: float


@dataclass(frozen=True)
class ResultadoModo:
    nota_A: float
    nota_B: float
    nota_C: float
    nota_D: float
    nota_E: float
    nota_F: float
    nota_G: float
    nota_H: float
    nota_I: float
    nota_J: float
    nota_K: float
    nota_M: float
    nota_N: float
    nota_O: float | None
    nota_P: float
    nota_Q: float
    nota_restriccion: float
    nota_atraccion: float
    nota_final: float

    def desglose(self) -> dict[str, float]:
        datos = {
            "A_fonotactica": self.nota_A,
            "B_rima_asonancia": self.nota_B,
            "C_repeticion": self.nota_C,
            "D_clusters": self.nota_D,
            "E_ritmo": self.nota_E,
            "F_behaghel": self.nota_F,
            "G_sandhi": self.nota_G,
            "H_sonoridad": self.nota_H,
            "I_balance_cv": self.nota_I,
            "J_perfil_silabico": self.nota_J,
            "K_fluidez": self.nota_K,
            "M_ritmo_prototipico": self.nota_M,
            "N_agrupacion": self.nota_N,
            "P_curva_sonoridad": self.nota_P,
            "Q_suavidad_union": self.nota_Q,
            "restriccion": self.nota_restriccion,
            "atraccion": self.nota_atraccion,
            "final": self.nota_final,
        }
        if self.nota_O is not None:
            datos["O_compacidad"] = self.nota_O
        return datos


@dataclass(frozen=True)
class ResultadoEvaluacion:
    nombre: str
    apellido1: str
    apellido2: str
    piezas: tuple[str, str, str]
    corto: ResultadoModo
    completo: ResultadoModo

    @property
    def nota_A(self) -> float:
        return self.completo.nota_A

    @property
    def nota_B(self) -> float:
        return self.completo.nota_B

    @property
    def nota_C(self) -> float:
        return self.completo.nota_C

    @property
    def nota_D(self) -> float:
        return self.completo.nota_D

    @property
    def nota_E(self) -> float:
        return self.completo.nota_E

    @property
    def nota_F(self) -> float:
        return self.completo.nota_F

    @property
    def nota_G(self) -> float:
        return self.completo.nota_G

    @property
    def nota_final(self) -> float:
        return self.completo.nota_final

    def desglose(self) -> dict[str, float]:
        return self.completo.desglose()


@dataclass(frozen=True)
class FeaturesEvaluacion:
    """Señales crudas para modelado supervisado (sin mapeos 0–100)."""

    nombre: str
    apellido1: str
    apellido2: str
    # Eje 1 — Juntura (CALCE: unión nombre|apellido1)
    logbigram_union: float
    tipo_contacto: str
    # Eje 2 — Ritmo/longitud
    n_sil_nombre: int  # INTRÍNSECA
    n_sil_ap1: int  # CALCE
    n_sil_ap2: int  # CALCE (modo completo)
    # Eje 3 — Sonoridad (INTRÍNSECA)
    sonoridad_nombre: float
    # Eje 4 — Eco/rima (CALCE)
    eco_vocal_union: float
    rima_completa_ap1: float
    rima_vocalica_ap1: float
    rima_completa_ap2: float
    rima_vocalica_ap2: float

    def to_dict(self) -> dict[str, str | int | float]:
        return {
            "nombre": self.nombre,
            "apellido1": self.apellido1,
            "apellido2": self.apellido2,
            "logbigram_union": self.logbigram_union,
            "tipo_contacto": self.tipo_contacto,
            "n_sil_nombre": self.n_sil_nombre,
            "n_sil_ap1": self.n_sil_ap1,
            "n_sil_ap2": self.n_sil_ap2,
            "sonoridad_nombre": self.sonoridad_nombre,
            "eco_vocal_union": self.eco_vocal_union,
            "rima_completa_ap1": self.rima_completa_ap1,
            "rima_vocalica_ap1": self.rima_vocalica_ap1,
            "rima_completa_ap2": self.rima_completa_ap2,
            "rima_vocalica_ap2": self.rima_vocalica_ap2,
        }


class LexicoFonotactico:
    """Bigramas/trigramas y estadisticas del catalogo para criterios A, D, H y K."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._bigramas: dict[tuple[str, str], int] = {}
        self._trigramas: dict[tuple[str, str, str], int] = {}
        self._total_bigramas = 0
        self._log_bigramas: list[float] = []
        self._log_trigramas: list[float] = []
        self._p5_bigrama = -8.0
        self._p75_bigrama = -4.0
        self._p95_bigrama = -2.0
        self._p1_trigrama = -12.0
        self.mediana_sonoridad = 0.55
        self._construir(conn)

    def _construir(self, conn: sqlite3.Connection) -> None:
        vocabulario: set[str] = set()
        ratios_sonoridad: list[float] = []

        for (fonetica,) in conn.execute(
            "SELECT DISTINCT fonetica FROM nombres WHERE fonetica IS NOT NULL AND fonetica != ''"
        ):
            tokens, _ = tokenizar_ipa(fonetica)
            if len(tokens) < 2:
                continue
            vocabulario.update(tokens)
            ratios_sonoridad.append(_ratio_sonoridad(tokens))
            for i in range(len(tokens) - 1):
                bigrama = (tokens[i], tokens[i + 1])
                self._bigramas[bigrama] = self._bigramas.get(bigrama, 0) + 1
                self._total_bigramas += 1
            for i in range(len(tokens) - 2):
                trigrama = (tokens[i], tokens[i + 1], tokens[i + 2])
                self._trigramas[trigrama] = self._trigramas.get(trigrama, 0) + 1

        alfabeto = sorted(vocabulario) or ["a"]
        vocab_size = len(alfabeto)

        for count in self._bigramas.values():
            self._log_bigramas.append(math.log(count / self._total_bigramas))

        total_tri = sum(self._trigramas.values()) or 1
        for count in self._trigramas.values():
            self._log_trigramas.append(math.log(count / total_tri))

        self._alfabeto = alfabeto
        self._vocab_size = vocab_size
        self._default_log_bigrama = math.log(1 / (self._total_bigramas + vocab_size**2))
        self._default_log_trigrama = math.log(1 / (total_tri + vocab_size**3))

        if self._log_bigramas:
            ordenados = sorted(self._log_bigramas)
            n = len(ordenados)
            self._p5_bigrama = ordenados[max(0, int(n * 0.05) - 1)]
            self._p75_bigrama = ordenados[min(n - 1, int(n * 0.75))]
            self._p95_bigrama = ordenados[min(n - 1, int(n * 0.95))]
        if self._log_trigramas:
            ordenados = sorted(self._log_trigramas)
            self._p1_trigrama = ordenados[max(0, int(len(ordenados) * 0.01) - 1)]

        if ratios_sonoridad:
            ordenados = sorted(ratios_sonoridad)
            mid = len(ordenados) // 2
            if len(ordenados) % 2:
                self.mediana_sonoridad = ordenados[mid]
            else:
                self.mediana_sonoridad = (ordenados[mid - 1] + ordenados[mid]) / 2

    def log_bigrama(self, a: str, b: str) -> float:
        count = self._bigramas.get((a, b), 0)
        if count == 0:
            return self._default_log_bigrama
        return math.log(count / self._total_bigramas)

    def log_trigrama(self, a: str, b: str, c: str) -> float:
        count = self._trigramas.get((a, b, c), 0)
        total_tri = sum(self._trigramas.values()) or 1
        if count == 0:
            return self._default_log_trigrama
        return math.log(count / total_tri)

    def trigrama_es_raro(self, a: str, b: str, c: str) -> bool:
        return self.log_trigrama(a, b, c) <= self._p1_trigrama

    def media_log_bigramas_union(self, izq: PiezaFonetica, der: PiezaFonetica) -> float:
        if not izq.tokens or not der.tokens:
            return self._default_log_bigrama
        logs: list[float] = []
        a = izq.tokens
        b = der.tokens
        if len(a) >= 2:
            logs.append(self.log_bigrama(a[-2], a[-1]))
        logs.append(self.log_bigrama(a[-1], b[0]))
        if len(b) >= 2:
            logs.append(self.log_bigrama(b[0], b[1]))
        return sum(logs) / len(logs)

    def nota_bigramas_union(self, izq: PiezaFonetica, der: PiezaFonetica) -> float:
        media = self.media_log_bigramas_union(izq, der)
        return _mapear_rango(media, self._p5_bigrama, self._p95_bigrama)

    def nota_fluidez_k(self, log_media: float) -> float:
        return _mapear_rango(log_media, self._p75_bigrama, self._p95_bigrama, base=50.0)


_LEXICO: LexicoFonotactico | None = None


def obtener_lexico(conn: sqlite3.Connection | None = None) -> LexicoFonotactico:
    global _LEXICO
    if _LEXICO is not None:
        return _LEXICO
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        try:
            _LEXICO = LexicoFonotactico(conn)
        finally:
            conn.close()
    else:
        _LEXICO = LexicoFonotactico(conn)
    return _LEXICO


def es_vocal(fonema: str) -> bool:
    return fonema in VOCALES


def es_consonante(fonema: str) -> bool:
    return bool(fonema) and fonema not in VOCALES and fonema not in MARCAS_ACENTO


def tokenizar_ipa(ipa: str) -> tuple[list[str], dict[int, str]]:
    tokens: list[str] = []
    acentos: dict[int, str] = {}
    for char in ipa.strip():
        if char in MARCAS_ACENTO:
            acentos[len(tokens)] = "primary" if char == "ˈ" else "secondary"
            continue
        if char.isspace():
            continue
        tokens.append(char)
    return tokens, acentos


def _indice_vocal_tonica(
    tokens: list[str], acentos: dict[int, str]
) -> int | None:
    for idx, tipo in sorted(acentos.items()):
        if tipo != "primary":
            continue
        if idx < len(tokens) and es_vocal(tokens[idx]):
            return idx
    return None


def _forman_diptongo(
    v1: str,
    v2: str,
    idx1: int,
    idx2: int,
    tonica_idx: int | None,
) -> bool:
    if v1 in VOCALES_FUERTES and v2 in VOCALES_FUERTES:
        return False
    if tonica_idx is not None:
        if idx1 == tonica_idx and v1 in VOCALES_DEBILES and v2 in VOCALES_FUERTES:
            return False
        if idx2 == tonica_idx and v2 in VOCALES_DEBILES and v1 in VOCALES_FUERTES:
            return False
    return True


def _nucleos_vocalicos(
    tokens: list[str], tonica_idx: int | None
) -> list[tuple[int, int]]:
    indices_vocal = [i for i, t in enumerate(tokens) if es_vocal(t)]
    if not indices_vocal:
        return []

    nucleos: list[tuple[int, int]] = []
    pos = 0
    while pos < len(indices_vocal):
        inicio = indices_vocal[pos]
        fin = inicio
        while pos + 1 < len(indices_vocal):
            siguiente = indices_vocal[pos + 1]
            if siguiente != fin + 1:
                break
            v1, v2 = tokens[fin], tokens[siguiente]
            if not _forman_diptongo(v1, v2, fin, siguiente, tonica_idx):
                break
            fin = siguiente
            pos += 1
        nucleos.append((inicio, fin))
        pos += 1
    return nucleos


def silabificar(
    tokens: list[str], tonica_idx: int | None = None
) -> list[list[str]]:
    if not tokens:
        return []

    nucleos = _nucleos_vocalicos(tokens, tonica_idx)
    if not nucleos:
        return [list(tokens)]

    silabas: list[list[str]] = []
    for i, (n_inicio, n_fin) in enumerate(nucleos):
        sil_inicio = 0 if i == 0 else nucleos[i - 1][1] + 1
        silabas.append(list(tokens[sil_inicio : n_fin + 1]))

    ultimo_fin = nucleos[-1][1]
    if ultimo_fin + 1 < len(tokens):
        silabas[-1].extend(tokens[ultimo_fin + 1 :])

    return silabas


def nucleo_vocalico(silaba: list[str]) -> list[str]:
    return [f for f in silaba if es_vocal(f)]


def coda(silaba: list[str]) -> list[str]:
    vocales_vistas = False
    coda_fonemas: list[str] = []
    for f in silaba:
        if es_vocal(f):
            vocales_vistas = True
        elif vocales_vistas:
            coda_fonemas.append(f)
    return coda_fonemas


def analizar_pieza(texto: str, ipa: str) -> PiezaFonetica:
    tokens, acentos = tokenizar_ipa(ipa)
    tonica_idx = _indice_vocal_tonica(tokens, acentos)
    silabas = silabificar(tokens, tonica_idx)
    indice_acento: int | None = None
    if tonica_idx is not None:
        acum = 0
        for i, sil in enumerate(silabas):
            if tonica_idx < acum + len(sil):
                indice_acento = i
                break
            acum += len(sil)
    return PiezaFonetica(
        texto=texto,
        ipa=ipa,
        tokens=tuple(tokens),
        silabas=tuple(tuple(s) for s in silabas),
        indice_acento=indice_acento,
    )


def _clamp(nota: float, minimo: float = 0.0, maximo: float = 100.0) -> float:
    return max(minimo, min(maximo, nota))


def _mapear_rango(
    valor: float,
    bajo: float,
    alto: float,
    base: float = 0.0,
    techo: float = 100.0,
) -> float:
    if alto <= bajo:
        return (base + techo) / 2
    if valor <= bajo:
        return base
    if valor >= alto:
        return techo
    return base + (techo - base) * (valor - bajo) / (alto - bajo)


def _valor_sonoridad(fonema: str) -> float:
    if es_vocal(fonema):
        return 5.0
    if fonema in SONORANTES:
        return 4.0
    if fonema in "bdg":
        return 2.5
    if fonema in OBSTRUYENTES_SORDOS:
        return 1.0
    return 2.0


def _ratio_sonoridad(tokens: tuple[str, ...] | list[str]) -> float:
    fonemas = [t for t in tokens if t not in MARCAS_ACENTO]
    if not fonemas:
        return 0.0
    sonoros = sum(1 for t in fonemas if _valor_sonoridad(t) >= 4.0)
    return sonoros / len(fonemas)


def _nota_rima_union(izq: PiezaFonetica, der: PiezaFonetica) -> float:
    if not izq.silabas or not der.silabas:
        return 100.0
    ultima = list(izq.silabas[-1])
    primera = list(der.silabas[0])
    nuc_u = nucleo_vocalico(ultima)
    nuc_p = nucleo_vocalico(primera)
    if not nuc_u or not nuc_p:
        return 100.0
    coda_u, coda_p = coda(ultima), coda(primera)
    if nuc_u == nuc_p and coda_u and coda_u == coda_p:
        return 0.0
    if nuc_u == nuc_p:
        return 40.0
    if nuc_u[-1] == nuc_p[0]:
        return 70.0
    return 100.0


def _nota_repeticion_union(izq: PiezaFonetica, der: PiezaFonetica) -> float:
    if not izq.tokens or not der.tokens:
        return 100.0
    nota = 100.0
    if izq.tokens[-1] == der.tokens[0]:
        nota -= 50
    if izq.tokens[-2:] == der.tokens[:2] and len(izq.tokens) >= 2 and len(der.tokens) >= 2:
        return 0.0
    if izq.silabas and der.silabas and list(izq.silabas[-1]) == list(der.silabas[0]):
        nota -= 80
    return _clamp(nota)


def _cluster_legal_es(c1: str, c2: str) -> bool:
    par = c1 + c2
    if par in CLUSTERS_RAROS:
        return False
    if par in ONSETS_LEGALES:
        return True
    if c1 == "s" and c2 in "ptkbf":
        return True
    return False


def _nota_clusters_union(
    izq: PiezaFonetica, der: PiezaFonetica, lexico: LexicoFonotactico
) -> float:
    if not izq.tokens or not der.tokens:
        return 100.0
    nota = 100.0
    c1, c2 = izq.tokens[-1], der.tokens[0]
    if es_consonante(c1) and es_consonante(c2):
        if c1 == c2:
            nota -= 30
        elif not _cluster_legal_es(c1, c2):
            nota -= 30
    par = c1 + c2
    if par in CLUSTERS_RAROS:
        nota -= 30
    if len(izq.tokens) >= 2:
        tri = (izq.tokens[-2], izq.tokens[-1], der.tokens[0])
        if lexico.trigrama_es_raro(*tri):
            nota -= 50
    return _clamp(nota)


def _nota_sandhi_union(izq: PiezaFonetica, der: PiezaFonetica) -> float:
    if not izq.tokens or not der.tokens:
        return 100.0
    c1, c2 = izq.tokens[-1], der.tokens[0]
    v1, v2 = es_vocal(c1), es_vocal(c2)
    if not v1 and v2:
        return 100.0
    if v1 and not v2:
        return 90.0
    if v1 and v2:
        return 40.0 if c1 == c2 else 60.0
    if _cluster_legal_es(c1, c2):
        return 50.0
    return 10.0


def _tipo_contacto_union(izq: PiezaFonetica, der: PiezaFonetica) -> str:
    """Categoría cruda del contacto en la unión (eje juntura)."""
    if not izq.tokens or not der.tokens:
        return "CV"
    c1, c2 = izq.tokens[-1], der.tokens[0]
    v1, v2 = es_vocal(c1), es_vocal(c2)
    if not v1 and v2:
        return "CV"
    if v1 and not v2:
        return "VC"
    if v1 and v2:
        return "VV_same" if c1 == c2 else "VV_dist"
    par = c1 + c2
    if par in CLUSTERS_RAROS or not _cluster_legal_es(c1, c2):
        return "CC_illegal"
    return "CC_legal"


def _eco_vocal_union(izq: PiezaFonetica, der: PiezaFonetica) -> float:
    """Similitud continua [0,1] entre núcleos vocálicos en la frontera nombre|ap1."""
    if not izq.silabas or not der.silabas:
        return 0.0
    nuc_u = nucleo_vocalico(list(izq.silabas[-1]))
    nuc_p = nucleo_vocalico(list(der.silabas[0]))
    if not nuc_u or not nuc_p:
        return 0.0
    if nuc_u == nuc_p:
        return 1.0
    comunes = [v for v in nuc_u if v in nuc_p]
    if not comunes:
        return 0.0
    return len(comunes) / max(len(nuc_u), len(nuc_p))


def _cola_rimica(pieza: PiezaFonetica) -> tuple[str, ...]:
    """Fonemas desde el núcleo de la sílaba tónica hasta el final de la pieza."""
    tokens = list(pieza.tokens)
    if not tokens or not pieza.silabas:
        return tuple()
    idx_sil = pieza.indice_acento
    if idx_sil is None:
        idx_sil = len(pieza.silabas) - 1
    silabas = [list(s) for s in pieza.silabas]
    sil_tonica = silabas[idx_sil]
    offset = sum(len(silabas[k]) for k in range(idx_sil))
    for i, token in enumerate(sil_tonica):
        if es_vocal(token):
            return tuple(tokens[offset + i :])
    return tuple(tokens[offset:])


def _similitud_cola_fonemas(
    cola_izq: tuple[str, ...], cola_der: tuple[str, ...]
) -> float:
    """Coincidencias posicionales / longitud de la cola más larga."""
    if not cola_izq or not cola_der:
        return 0.0
    if cola_izq == cola_der:
        return 1.0
    limite = min(len(cola_izq), len(cola_der))
    coincidencias = sum(1 for i in range(limite) if cola_izq[i] == cola_der[i])
    return coincidencias / max(len(cola_izq), len(cola_der))


def _rima_completa_entre(izq: PiezaFonetica, der: PiezaFonetica) -> float:
    return _similitud_cola_fonemas(_cola_rimica(izq), _cola_rimica(der))


def _rima_vocalica_entre(izq: PiezaFonetica, der: PiezaFonetica) -> float:
    cola_izq = _cola_rimica(izq)
    cola_der = _cola_rimica(der)
    voc_izq = tuple(t for t in cola_izq if es_vocal(t))
    voc_der = tuple(t for t in cola_der if es_vocal(t))
    return _similitud_cola_fonemas(voc_izq, voc_der)


def _nota_suavidad_q(izq: PiezaFonetica, der: PiezaFonetica) -> float:
    if not izq.tokens or not der.tokens:
        return 50.0
    ventana = list(izq.tokens[-2:]) + list(der.tokens[:2])
    sordas = sum(1 for f in ventana if f in OBSTRUYENTES_SORDOS)
    if sordas == 0:
        return 60.0
    if sordas == 1:
        return 55.0
    return max(50.0, 60.0 - (sordas - 1) * 10.0)


def evaluar_nucleo_union(
    nombre: PiezaFonetica,
    apellido1: PiezaFonetica,
    lexico: LexicoFonotactico,
) -> NucleoUnion:
    log_media = lexico.media_log_bigramas_union(nombre, apellido1)
    return NucleoUnion(
        nota_A=round(lexico.nota_bigramas_union(nombre, apellido1), 1),
        nota_B=round(_nota_rima_union(nombre, apellido1), 1),
        nota_C=round(_nota_repeticion_union(nombre, apellido1), 1),
        nota_D=round(_nota_clusters_union(nombre, apellido1, lexico), 1),
        nota_G=round(_nota_sandhi_union(nombre, apellido1), 1),
        nota_K=round(lexico.nota_fluidez_k(log_media), 1),
        nota_Q=round(_nota_suavidad_q(nombre, apellido1), 1),
        log_bigrama_union=log_media,
    )


def _distancia_plantilla(conteos: tuple[int, ...], plantillas: tuple[tuple[int, ...], ...]) -> float:
    if not conteos:
        return 1.0
    min_dist = min(
        sum(abs(a - b) for a, b in zip(conteos, plant)) + abs(len(conteos) - len(plant)) * 2
        for plant in plantillas
    )
    return min_dist / 4.0


def nota_criterio_e(
    piezas: list[PiezaFonetica],
    plantillas: tuple[tuple[int, ...], ...],
    *,
    penalizar_nombre_largo: bool = False,
) -> float:
    conteos = tuple(len(p.silabas) for p in piezas)
    penalizacion = _distancia_plantilla(conteos, plantillas) * 0.4

    if penalizar_nombre_largo and len(piezas) >= 3:
        sil_nombre = len(piezas[0].silabas)
        sil_apellidos = len(piezas[1].silabas) + len(piezas[2].silabas)
        if sil_nombre > sil_apellidos:
            penalizacion += 0.2

    acentos_finales = 0
    for pieza in piezas:
        if pieza.indice_acento is not None and pieza.silabas:
            if pieza.indice_acento == len(pieza.silabas) - 1:
                acentos_finales += 1
    if acentos_finales == len(piezas):
        penalizacion += 0.25

    return _clamp(100.0 * (1.0 - min(1.0, penalizacion)))


def nota_criterio_f(
    nombre: PiezaFonetica,
    apellido1: PiezaFonetica,
    apellido2: PiezaFonetica | None = None,
) -> float:
    sil_nombre = len(nombre.silabas) or 1
    sil_ap1 = len(apellido1.silabas) or 1
    ratio = sil_nombre / sil_ap1
    if ratio <= 1.0:
        nota = 100.0
    elif ratio <= 1.5:
        nota = 70.0
    elif ratio <= 2.0:
        nota = 40.0
    else:
        nota = 20.0
    if apellido2 is not None:
        sil_ap2 = len(apellido2.silabas) or 1
        if sil_nombre > sil_ap1 + sil_ap2:
            nota -= 15
    return _clamp(nota)


def nota_criterio_h(nombre: PiezaFonetica, lexico: LexicoFonotactico) -> float:
    ratio = _ratio_sonoridad(nombre.tokens)
    if lexico.mediana_sonoridad <= 0:
        return 75.0
    rel = ratio / lexico.mediana_sonoridad
    return _clamp(_mapear_rango(rel, 0.85, 1.15, base=50.0, techo=100.0))


def nota_criterio_i(nombre: PiezaFonetica) -> float:
    vocales = sum(1 for t in nombre.tokens if es_vocal(t))
    consonantes = sum(1 for t in nombre.tokens if es_consonante(t))
    if consonantes == 0:
        return 65.0
    ratio = vocales / consonantes
    if 0.8 <= ratio <= 1.4:
        dist = abs(ratio - 1.1) / 0.3
        return _clamp(50.0 + 50.0 * (1.0 - min(1.0, dist)))
    return _clamp(50.0 - 15.0 * min(1.0, abs(ratio - 1.1) / 0.6))


def nota_criterio_j(nombre: PiezaFonetica) -> float:
    n = len(nombre.silabas)
    if 2 <= n <= 4 and nombre.indice_acento is not None:
        bonus = 15.0 if n in (2, 3) else 10.0
        return _clamp(50.0 + bonus)
    if n == 1:
        return 55.0
    return 50.0


def nota_criterio_m(
    piezas: list[PiezaFonetica],
    plantillas: tuple[tuple[int, ...], ...],
) -> float:
    conteos = tuple(len(p.silabas) for p in piezas)
    dist = _distancia_plantilla(conteos, plantillas)
    return _clamp(100.0 - dist * 50.0, 50.0, 100.0)


def _tipo_acento(pieza: PiezaFonetica) -> str | None:
    if pieza.indice_acento is None or not pieza.silabas:
        return None
    n = len(pieza.silabas)
    idx = pieza.indice_acento
    if idx == n - 1:
        return "oxitona"
    if idx == n - 2:
        return "paroxitona"
    if idx == 0:
        return "proparoxitona"
    return "otro"


def nota_criterio_n(piezas: list[PiezaFonetica]) -> float:
    nota = 50.0
    acentos = [_tipo_acento(p) for p in piezas]
    if None in acentos:
        return nota
    if acentos[0] == "oxitona" and all(a == "paroxitona" for a in acentos[1:]):
        nota += 15.0
    elif acentos[0] == "paroxitona" and all(a == "paroxitona" for a in acentos[1:]):
        nota += 10.0
    elif len(set(acentos)) == 1:
        nota += 5.0
    return _clamp(nota)


def nota_criterio_o(piezas: list[PiezaFonetica]) -> float:
    total = sum(len(p.silabas) for p in piezas)
    if 6 <= total <= 10:
        return _clamp(50.0 + 50.0 * (1.0 - abs(total - 8) / 2.0))
    dist = abs(total - 8)
    return _clamp(50.0 - dist * 5.0)


def nota_criterio_p(piezas: list[PiezaFonetica]) -> float:
    tokens: list[str] = []
    for pieza in piezas:
        tokens.extend(pieza.tokens)
    if not tokens:
        return 50.0
    media = sum(_valor_sonoridad(t) for t in tokens) / len(tokens)
    return _clamp(_mapear_rango(media, 2.0, 4.2, base=50.0, techo=100.0))


def _pesos_atraccion(incluir_o: bool) -> dict[str, float]:
    pesos = dict(PESOS_ATRACCION_BASE)
    if not incluir_o:
        pesos.pop("O", None)
    total = sum(pesos.values())
    return {k: v / total for k, v in pesos.items()}


def calcular_nota_restriccion(notas: dict[str, float]) -> float:
    total = sum(PESOS[k] * notas[k] for k in PESOS)
    return round(_clamp(total), 1)


def calcular_nota_atraccion(notas: dict[str, float], *, incluir_o: bool) -> float:
    pesos = _pesos_atraccion(incluir_o)
    total = sum(pesos[k] * notas[k] for k in pesos)
    return round(_clamp(total), 1)


def calcular_nota_final_capas(nota_restriccion: float, nota_atraccion: float) -> float:
    final = (
        PESO_RESTRICCION_CAPA * nota_restriccion
        + PESO_ATRACCION_CAPA * nota_atraccion
    )
    return round(_clamp(final), 1)


def _construir_resultado_modo(
    notas_restriccion: dict[str, float],
    notas_atraccion: dict[str, float],
    *,
    incluir_o: bool,
) -> ResultadoModo:
    nota_restriccion = calcular_nota_restriccion(notas_restriccion)
    nota_atraccion = calcular_nota_atraccion(notas_atraccion, incluir_o=incluir_o)
    nota_final = calcular_nota_final_capas(nota_restriccion, nota_atraccion)
    return ResultadoModo(
        nota_A=notas_restriccion["A"],
        nota_B=notas_restriccion["B"],
        nota_C=notas_restriccion["C"],
        nota_D=notas_restriccion["D"],
        nota_E=notas_restriccion["E"],
        nota_F=notas_restriccion["F"],
        nota_G=notas_restriccion["G"],
        nota_H=notas_atraccion["H"],
        nota_I=notas_atraccion["I"],
        nota_J=notas_atraccion["J"],
        nota_K=notas_atraccion["K"],
        nota_M=notas_atraccion["M"],
        nota_N=notas_atraccion["N"],
        nota_O=notas_atraccion.get("O") if incluir_o else None,
        nota_P=notas_atraccion["P"],
        nota_Q=notas_atraccion["Q"],
        nota_restriccion=nota_restriccion,
        nota_atraccion=nota_atraccion,
        nota_final=nota_final,
    )


def evaluar_modo_corto(
    piezas: list[PiezaFonetica],
    nucleo: NucleoUnion,
    lexico: LexicoFonotactico,
) -> ResultadoModo:
    nombre, ap1 = piezas[0], piezas[1]
    notas_restriccion = {
        "A": nucleo.nota_A,
        "B": nucleo.nota_B,
        "C": nucleo.nota_C,
        "D": nucleo.nota_D,
        "E": round(nota_criterio_e([nombre, ap1], PLANTILLAS_CORTO), 1),
        "F": round(nota_criterio_f(nombre, ap1), 1),
        "G": nucleo.nota_G,
    }
    notas_atraccion = {
        "H": round(nota_criterio_h(nombre, lexico), 1),
        "I": round(nota_criterio_i(nombre), 1),
        "J": round(nota_criterio_j(nombre), 1),
        "K": nucleo.nota_K,
        "M": round(nota_criterio_m([nombre, ap1], PLANTILLAS_CORTO), 1),
        "N": round(nota_criterio_n([nombre, ap1]), 1),
        "P": round(nota_criterio_p([nombre, ap1]), 1),
        "Q": nucleo.nota_Q,
    }
    return _construir_resultado_modo(
        notas_restriccion,
        notas_atraccion,
        incluir_o=False,
    )


def evaluar_modo_completo(
    piezas: list[PiezaFonetica],
    nucleo: NucleoUnion,
    lexico: LexicoFonotactico,
    corto: ResultadoModo,
) -> ResultadoModo:
    nombre, ap1, ap2 = piezas[0], piezas[1], piezas[2]
    notas_restriccion = {
        "A": corto.nota_A,
        "B": corto.nota_B,
        "C": corto.nota_C,
        "D": corto.nota_D,
        "E": round(
            nota_criterio_e(
                piezas,
                PLANTILLAS_COMPLETO,
                penalizar_nombre_largo=True,
            ),
            1,
        ),
        "F": round(nota_criterio_f(nombre, ap1, ap2), 1),
        "G": corto.nota_G,
    }
    notas_atraccion = {
        "H": corto.nota_H,
        "I": corto.nota_I,
        "J": corto.nota_J,
        "K": corto.nota_K,
        "M": round(nota_criterio_m(piezas, PLANTILLAS_COMPLETO), 1),
        "N": round(nota_criterio_n(piezas), 1),
        "O": round(nota_criterio_o(piezas), 1),
        "P": round(nota_criterio_p(piezas), 1),
        "Q": corto.nota_Q,
    }
    return _construir_resultado_modo(
        notas_restriccion,
        notas_atraccion,
        incluir_o=True,
    )


def extraer_features(
    nombre: str,
    apellido1: str,
    apellido2: str,
    ipa_piezas: tuple[str, str, str],
    lexico: LexicoFonotactico | None = None,
) -> FeaturesEvaluacion:
    """Extrae señales crudas (5 ejes) sin pasar por criterios A–Q cocinados."""
    if lexico is None:
        lexico = obtener_lexico()
    piezas = [
        analizar_pieza(nombre, ipa_piezas[0]),
        analizar_pieza(apellido1, ipa_piezas[1]),
        analizar_pieza(apellido2, ipa_piezas[2]),
    ]
    nom, ap1, ap2 = piezas[0], piezas[1], piezas[2]
    return FeaturesEvaluacion(
        nombre=nombre,
        apellido1=apellido1,
        apellido2=apellido2,
        logbigram_union=lexico.media_log_bigramas_union(nom, ap1),
        tipo_contacto=_tipo_contacto_union(nom, ap1),
        n_sil_nombre=len(nom.silabas),
        n_sil_ap1=len(ap1.silabas),
        n_sil_ap2=len(ap2.silabas),
        sonoridad_nombre=_ratio_sonoridad(nom.tokens),
        eco_vocal_union=_eco_vocal_union(nom, ap1),
        rima_completa_ap1=_rima_completa_entre(nom, ap1),
        rima_vocalica_ap1=_rima_vocalica_entre(nom, ap1),
        rima_completa_ap2=_rima_completa_entre(nom, ap2),
        rima_vocalica_ap2=_rima_vocalica_entre(nom, ap2),
    )


def evaluar_combinacion(
    nombre: str,
    apellido1: str,
    apellido2: str,
    ipa_piezas: tuple[str, str, str],
    lexico: LexicoFonotactico | None = None,
) -> ResultadoEvaluacion:
    if lexico is None:
        lexico = obtener_lexico()
    piezas = [
        analizar_pieza(nombre, ipa_piezas[0]),
        analizar_pieza(apellido1, ipa_piezas[1]),
        analizar_pieza(apellido2, ipa_piezas[2]),
    ]
    nucleo = evaluar_nucleo_union(piezas[0], piezas[1], lexico)
    corto = evaluar_modo_corto(piezas[:2], nucleo, lexico)
    completo = evaluar_modo_completo(piezas, nucleo, lexico, corto)
    return ResultadoEvaluacion(
        nombre=nombre,
        apellido1=apellido1,
        apellido2=apellido2,
        piezas=ipa_piezas,
        corto=corto,
        completo=completo,
    )
