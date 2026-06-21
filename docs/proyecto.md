# seleccionador-nombres — estado del proyecto

Base de datos de nombres hispanos + evaluación fonética y ranking dado un par de apellidos. **Destino:** web app con ranking aprendido (features + preferencias pairwise); **baseline actual:** scoring heurístico v2 en `fonetica_scoring.py`.

---

## Objetivos

| # | Objetivo | Estado |
|---|----------|--------|
| 1 | Catálogo de tokens simples con género M/F | ✅ ~215k filas |
| 2 | Metadatos por fuente en tablas separadas | Parcial (`familiaridad` desde guaguas) |
| 3 | Fonética IPA (`es-419`) por nombre | ✅ |
| 4 | Ranking nombre + apellidos | Baseline v2 ✅; ranker aprendido pendiente |

---

## Infraestructura

### SQLite (`data/db/nombres.db`)

**`nombres`:** `id`, `nombre` (MAYÚSCULAS con tildes), `genero` (M/F), `fonetica`. Unicidad `(nombre, genero)`. Compuestos en fuente → tokens por espacio.

**`familiaridad`** (FK → `nombres.id`):

| Columna | Descripción |
|---------|-------------|
| `prevalencia` | Σ `exp(−(2021−año)/30) × proporcion` desde guaguas |
| `log_familiaridad` | `log(1e-6 + prevalencia)` |
| `prop_reciente` | Media `proporcion` en 2010–2021 |

Población: `poblar_familiaridad.py` (re-ejecutar tras `rebuild_nombres.py`). Lookup: `familiaridad_de()` en `lib/familiaridad.py`.

### Fuentes del catálogo

URLs en [`data/raw/fuentes.txt`](../data/raw/fuentes.txt). Estructura `data/`: [`README`](../data/README.md).

| Fuente | Contribución (~pares únicos) | En git |
|--------|------------------------------|--------|
| España 2012 (CSV M+F) | ~17k | ✅ |
| Chile guaguas | ~205k | CSV completo gitignored; `guaguas_frecuentes.csv` versionado |
| España 2025 (INE xlsx) | ~22k | gitignored |
| **Total deduplicado** | **~215k** | |

Pendiente integrar: `ergobaby-2024.txt`, `bio-bio-2024.txt`.

### Fonética

phonemizer + espeak-ng, dialecto **`es-419`** (`phonemizer_config.py`). Setup: `setup_espeak.py`. Población: `poblar_fonetica.py`. Apellidos se fonetizan en runtime al evaluar.

### Scripts clave

Ver [`scripts/README.md`](../scripts/README.md).

| Carpeta | Rol |
|---------|-----|
| `lib/` | `fonetica_scoring.py`, `familiaridad.py`, `phonemizer_config.py`, … |
| `bdd/` | `rebuild_nombres.py`, `poblar_fonetica.py`, `poblar_familiaridad.py` |
| `evaluacion/` | `evaluar_combinacion.py`, `evaluar_lote.py`, `evaluar_cruzada.py`, `export_csv.py`, `exportar_features.py` |
| `dev/` | `verificar_features.py`, análisis cruzada 10k |

Schema: `001_nombres.sql`, `002_fonetica.sql`, `003_familiaridad.sql`.

### Flujo habitual

```bash
pip install -r requirements.txt
python scripts/setup/setup_espeak.py
python scripts/bdd/rebuild_nombres.py
python scripts/bdd/poblar_fonetica.py
python scripts/bdd/poblar_familiaridad.py   # requiere guaguas.csv
# Si falta guaguas: python scripts/una_vez/download_guaguas.py
```

Tras `rebuild_nombres.py` → repoblar fonética y familiaridad.

---

## Decisiones de diseño

| Tema | Decisión |
|------|----------|
| Compuestos | Descomponer; catálogo = tokens |
| Tildes | `JOSÉ` ≠ `JOSE` |
| Unión puntuada | Solo `nombre\|apellido1` (nunca `ap1\|ap2`) |
| Modos | **Corto** (nom+ap1) / **Completo** (nom+ap1+ap2) |
| Scoring v2 | Baseline heurístico; no es el ranker final |
| Features ML | Señales crudas → modelo aprende pesos |
| Modelado | **A:** `w_global` (LLM+humano) · **C:** `w_user` (app) |
| BD | SQLite; PostgreSQL más adelante (`schema/postgres/` referencia) |
| Gitignore | `data/db/`, `outputs/`, `guaguas.csv`, xlsx INE, `vendor/espeak-ng/` |

---

## Scoring v2 (baseline)

Implementado en `lib/fonetica_scoring.py`. Referencia y comparación; el producto usará ranker aprendido.

### Arquitectura

- **Restricción (A–G):** ¿suena mal? Escala 0–100, 100 = sin problema.
- **Atracción (H–Q):** ¿suena bien? Escala 50 = neutro → 100.
- `nota_final = 0,70 × restricción + 0,30 × atracción`
- Unión A–G, K, Q: solo `nombre|apellido1`.

| Modo | Piezas | Uso |
|------|--------|-----|
| Corto | 2 | Prioriza apellido1 |
| Completo | 3 | Identidad legal entera |

### Criterios (resumen)

| ID | Nombre | Capa | Idea operativa |
|----|--------|------|----------------|
| A | Fonotáctica unión | R | Log-bigramas en unión; percentiles p5–p95 |
| B | Anti-rima | R | Rima plena → 0; asonancia → 40; nada → 100 |
| C | Anti-repetición | R | Eco fonema/sílaba en `\|` |
| D | Anti-cluster | R | CC ilegal, trigrama raro |
| E | Anti-ritmo | R | Lejos de plantillas silábicas favorables |
| F | Behaghel | R | Ratio sílabas nombre/ap1 |
| G | Sandhi | R | CV > VC > VV > CC |
| H | Sonoridad nombre | A | vs mediana catálogo |
| I | Balance CV | A | Banda 0,8–1,4 voc/conson |
| J | Perfil silábico | A | 2–4 sílabas |
| K | Fluidez (techo) | A | Bigramas frecuentes (p75–p95) |
| L | Familiaridad | — | Solo como **feature** ML, no en nota v2 |
| M | Ritmo prototípico | A | Distancia a plantillas (2,2), (3,2,2), … |
| N | Agrupación acento | A | Patrones oxítona/paroxítona |
| O | Compacidad | A | 6–10 sílabas totales (solo completo) |
| P | Curva sonoridad | A | Media ponderada frase |
| Q | Suavidad unión | A | Obstruyentes sordas en ventana `\|` |
| R | Maluma/takete | opt. | Fuera de nota global |

**Pesos restricción:** A 25%, B–E 15%, F 10%, G 5%. **Atracción:** K 25%, M 20%, H 15%, P/I/O 10%, J/N/Q ~3,3% (O solo completo).

Detalle de umbrales: código fuente `fonetica_scoring.py`.

### Hallazgos empíricos

- **v1:** media ~91, σ ~4 — poco discriminativo.
- **v2 + cruzada 10k:** η² nombre ~33%; niñas Spearman entre apellidos ~0,79; niños ~0,39.
- Rima onomástica: penalizar en B (polaco); no bonificar en atracción (Obermeier es poesía).

### Limitaciones

- Literatura: nombre + **un** apellido; extendemos a dos con reglas explícitas.
- No se puntúa calidad de `ap1|ap2`.
- Cambiar dialecto → `poblar_fonetica.py --force`.

---

## Features ML (`extraer_features`)

Señales crudas para Bradley–Terry; sin pesos fijos. API:

```python
extraer_features(nombre, ap1, ap2, ipa_piezas, genero, lexico=…, conn=…)
```

| Eje | Campos | Alcance |
|-----|--------|---------|
| Juntura | `logbigram_union`, `tipo_contacto` | `nombre\|ap1` |
| Ritmo | `n_sil_nombre`, `n_sil_ap1`, `n_sil_ap2` | Por pieza |
| Sonoridad | `sonoridad_nombre` | Nombre |
| Eco/rima | `eco_vocal_union`, `rima_completa_ap1/2`, `rima_vocalica_ap1/2` | Frontera y colas rímicas continuas [0,1] |
| Familiaridad | `log_familiaridad`, `prop_reciente` | Nombre (guaguas) |

Verificación: `scripts/dev/verificar_features.py` → `data/outputs/_verif_features.txt`.

---

## Modelo supervisado (plan A + C)

### Formato: comparaciones pairwise

| Tipo | Ejemplo | Prioridad |
|------|---------|-----------|
| **T1** | `Sofía` vs `Luna` | Opcional (filtro) |
| **T2** | `Sofía Tagle` vs `Luna Tagle` | Alta — modo corto |
| **T3** | `Sofía Tagle Díaz` vs `Luna Tagle Díaz` | Alta — modo completo |

Apellidos idénticos en ambos lados; solo cambia el nombre.

### Entrenamiento

\[
P(\text{A gana}) = \sigma\big(w \cdot (x_A - x_B)\big), \quad x = \text{extraer\_features()}
\]

**A — offline (`w_global`):** CSV unificado; LLM `α=1`, humano `α=10–20`; regresión logística en Δfeatures + L2.

**C — app (`w_user`):** `score = w_global·x + w_user·x`; update online tras cada par; ~25 pares/sesión.

Approach B (fine-tune en dos etapas): no prioritario.

### Bootstrap LLM

1. Muestreo estratificado T2/T3.
2. Prompt: eufonía al **decir en voz alta** (es-419); ignorar popularidad.
3. IPA en prompt recomendado para T2/T3 (ortografía engaña).
4. CSV: `tipo, ap1, ap2, genero, nombre_a, nombre_b, ganador, fuente`.

### UX web app (mismo formato)

Tras apellidos del bebé: T1 (6–8 pares) → T2 (8–12) → T3 (8–12) ≈ **25–30 clics**. Selección activa: pares con `P ≈ 0,5`. Respuestas → `w_user`.

### Riesgos

| Riesgo | Mitigación |
|--------|------------|
| LLM juzga fama/ortografía | IPA; anti-popularidad; `log_familiaridad` ya separa moda |
| Sesgo anglo | Validar pilot ~50 pares vs tu gusto |
| Pocos humanos | Ancla 50–100 pares T2/T3 con `α` alto |

### Validación

1. Acuerdo LLM vs ancla humana.
2. Spearman ranker vs humano vs baseline v2.
3. Simular sesión C (25 pares) sobre `w_global`.
4. Inspeccionar signo/magnitud de `w`.

---

## Referencias (selección)

| Tema | Referencia |
|------|------------|
| Eufonía nombre+apellido | [Polish names (UZ Zielona Góra)](https://www.zbc.uz.zgora.pl/dlibra/publication/104676/edition/93276), [Shropshire corpus](https://www.grin.com/document/456246) |
| Fonotáctica | [Hayes & Wilson](https://linguistics.ucla.edu/people/wilson/HayesWilsonMaximumEntropyPhonotactics.pdf), [UCI Calculator](https://phonotactics.socsci.uci.edu/) |
| Sandhi español | [PubMed vowel sandhi](https://pubmed.ncbi.nlm.nih.gov/41776154/), [RAE eufonía](https://www.rae.es/dhle/eufon%C3%ADa) |
| Agrado positivo | [Reber et al. fluency](https://pages.ucsd.edu/~pwinkiel/reber-schwarz-winkielman-beauty-PSPR-2004.pdf), [Crystal phonaesthetics](https://davidcrystal.com/Files/BooksAndArticles/-4009.pdf), [Obermeier prosody](https://www.sciencedirect.com/science/article/pii/S0010027715300081) |
| Simbolismo sonoro (R) | [Sidhu & Pexman 2019](https://journals.sagepub.com/doi/10.1177/0963721419850134) |

---

## Próximos pasos

**Fase 1 — Bootstrap LLM (A):** `generar_pares_llm.py` → pilot 500–1k → ancla humana 50–100 pares.

**Fase 2 — Modelo global (A):** `entrenar_ranker.py` → export `w_global` → validación vs v2.

**Fase 3 — App (C):** `rank_nombres.py` → selección activa de pares → API sesión `w_user` → web app.

**Después:** refrescar `w_global` con pares agregados de usuarios; post-rebuild unificado; PostgreSQL / deploy.

---

## Repositorio

```
seleccionador-nombres/
├── data/{raw,intermedio,outputs,db}
├── docs/proyecto.md
├── schema/{001,002,003}_*.sql
├── scripts/{lib,bdd,evaluacion,setup,dev,una_vez}
├── vendor/espeak-ng/   # gitignored
└── requirements.txt
```

`docker-compose.yml` + `.env.example`: PostgreSQL futuro; no necesarios para SQLite actual.
