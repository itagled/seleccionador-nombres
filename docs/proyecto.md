# seleccionador-nombres — estado del proyecto

Repositorio para construir una base de datos de nombres de habla hispana y, eventualmente, recomendar nombres que suenen bien fonéticamente dado el par de apellidos de un recién nacido.

---

## Objetivo final

1. **Catálogo de nombres** únicos (simples, no compuestos), con género.
2. **Metadatos por fuente** (frecuencia, país, año, edad media, etc.) en tablas separadas — pendiente.
3. **Fonética (IPA)** de cada nombre — columna poblada (~215k filas).
4. **Script de ranking** que, dados dos apellidos, ordene qué nombres suenan mejor — prototipo en `evaluar_combinacion.py` / `evaluar_lote.py`; modelo v2 documentado abajo, pendiente de implementar por completo.

---

## Qué hay hecho

### Base de datos (SQLite)

- Archivo: `data/db/nombres.db` (generado por scripts, no editar a mano).
- Motor actual: **SQLite**. PostgreSQL queda para más adelante (`schema/postgres/` existe como referencia, no se usa).

### Tabla `nombres`

| Columna   | Tipo    | Descripción                                      |
|-----------|---------|--------------------------------------------------|
| `id`      | INTEGER | Clave interna                                    |
| `nombre`  | TEXT    | En MAYÚSCULAS, **con tildes** (`MARÍA` ≠ `MARIA`) |
| `genero`  | TEXT    | `M` o `F` (nunca unisex `U`)                     |
| `fonetica`| TEXT    | IPA vía phonemizer + espeak-ng (poblada)         |

- Unicidad: `(nombre, genero)`.
- Si un nombre aparece en masculinos y femeninos, hay **dos filas**.
- ~**215.023 filas** tras la última reconstrucción.

### Reglas de extracción de nombres

Desde cada fuente se toma el campo nombre y se **parte por espacios** (nombres compuestos → tokens sueltos). Luego se deduplica por `(nombre, genero)`.

Ejemplo: `MARIA CARMEN` → `MARIA`, `CARMEN`.

### Fuentes de datos

Registro canónico de URLs en [`data/raw/fuentes.txt`](../data/raw/fuentes.txt).

Estructura de `data/`: `raw/` (descargas), `intermedio/` (listas generadas), `outputs/` (resultados), `db/` (SQLite). Ver [`data/README.md`](../data/README.md).

#### Integradas en la tabla `nombres`

| Archivo local | Origen | URL | Notas |
|---------------|--------|-----|-------|
| `data/raw/nombres-masculinos-frecuencia-edad-2012.csv` | [marcboquet/spanish-names](https://github.com/marcboquet/spanish-names) | https://github.com/marcboquet/spanish-names/tree/master | Nombres masculinos en España; columnas `nombre`, `frec`, `edad_media`. ~25.400 filas. Contribuye ~17.332 pares únicos (nombre + género) al combinar con femeninos. |
| `data/raw/nombres-femeninos-frecuencia-edad-2012.csv` | [marcboquet/spanish-names](https://github.com/marcboquet/spanish-names) | https://github.com/marcboquet/spanish-names/tree/master | Nombres femeninos en España; mismas columnas. ~24.500 filas. |
| `data/raw/guaguas.csv` | Paquete R [guaguas](https://cran.r-project.org/package=guaguas) (Registro Civil de Chile) | https://cran.r-project.org/package=guaguas · https://rivaquiroga.github.io/guaguas/index.html | Primer nombre inscrito en Chile, 1920–2021. Columnas `anio`, `nombre`, `sexo`, `n`, `proporcion`. 858.782 filas. Descargado con `scripts/una_vez/download_guaguas.py`. |
| `data/raw/nombres_por_edad_media.xlsx` | INE España (censos de población) | https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736177009&menu=resultados&idp=1254735572981#_tabs-1254736195454 | Frecuencias nacionales a 01/01/2025; frecuencia ≥ 20. Hojas `Hombres` y `Mujeres`; columnas `Nombre`, `Frecuencia`, `Edad Media`. |

#### Descargadas, aún no integradas en `nombres`

| Archivo local | Origen | URL | Notas |
|---------------|--------|-----|-------|
| `data/raw/guaguas_frecuentes.csv` | Paquete R [guaguas](https://cran.r-project.org/package=guaguas) | https://cran.r-project.org/package=guaguas | Subconjunto de guaguas: nombres con ≥ 15 ocurrencias por año. 86.366 filas. Generado junto con `guaguas.csv` vía `scripts/una_vez/download_guaguas.py`. |
| `data/raw/bio-bio-2024.txt` | BioBioChile (Registro Civil Chile, 2024) | https://www.biobiochile.cl/noticias/servicios/toma-nota/2024/12/06/los-100-nombres-de-ninas-y-ninos-mas-inscritos-el-2024-en-chile-isabella-podria-superar-a-emma.shtml | Top 100 nombres por género con frecuencia. Pendiente integrar. |
| `data/raw/ergobaby-2024.txt` | Ergobaby Chile (Registro Civil Chile, 2024) | https://ergobaby.cl/blog/portabebes/los-100-nombres-mas-populares-para-ninos-ninas-en-2024 | Top 100 por género, sin frecuencia. Pendiente integrar. |

#### Resumen de contribución al catálogo (último rebuild)

| Fuente | Pares únicos (nombre + género) |
|--------|-------------------------------|
| España 2012 (CSV masculinos + femeninos) | ~17.332 |
| Chile guaguas (`guaguas.csv`) | ~204.797 |
| España 2025 (`nombres_por_edad_media.xlsx`) | ~22.269 |
| **Total combinado (deduplicado)** | **~215.023 filas** |

### Fonética

- Librería: **[phonemizer](https://github.com/bootphon/phonemizer)** + **espeak-ng**.
- Dialecto configurado: **`es-419`** (español latinoamericano). Alternativa: `es` (peninsular) en `scripts/lib/phonemizer_config.py` → constante `FONETICA_LANGUAGE`.
- espeak-ng local en `vendor/espeak-ng/` (gitignored); setup con `scripts/setup/setup_espeak.py`.
- Muestra de 100 nombres: `data/outputs/muestra_fonetica_100.csv` (`scripts/dev/muestra_fonetica.py`).
- Población de la columna: `scripts/bdd/poblar_fonetica.py` (~215k nombres únicos; re-ejecutar tras cada `rebuild_nombres.py`).

### Scripts

Índice completo: [`scripts/README.md`](../scripts/README.md).

| Carpeta | Uso | Scripts |
|---------|-----|---------|
| `scripts/lib/` | Módulos compartidos | `phonemizer_config.py`, `nombres_sources.py`, `fonetica_scoring.py`, `bootstrap.py` |
| `scripts/bdd/` | **Recurrente** — pipeline SQLite | `rebuild_nombres.py`, `import_nombres.py`, `poblar_fonetica.py` |
| `scripts/evaluacion/` | **Recurrente** — puntuación | `evaluar_combinacion.py`, `evaluar_lote.py` |
| `scripts/setup/` | Ocasional — entorno | `setup_espeak.py`, `install_espeak_windows.ps1` |
| `scripts/una_vez/` | Puntual / legacy | `download_guaguas.py`, `import_guaguas_nombres.py` |
| `scripts/dev/` | Desarrollo | `muestra_fonetica.py` |

### Esquema SQL

- `schema/001_nombres.sql` — tabla `nombres` (incluye `fonetica`).
- `schema/002_fonetica.sql` — referencia del `ALTER TABLE` para bases antiguas.

---

## Cómo usar (flujo habitual)

```bash
# Dependencias
pip install -r requirements.txt

# espeak-ng (solo la primera vez, o si falta vendor/)
python scripts/setup/setup_espeak.py

# Reconstruir catálogo de nombres desde fuentes
python scripts/bdd/rebuild_nombres.py

# Poblar fonética (solo filas con fonetica NULL)
python scripts/bdd/poblar_fonetica.py

# Prueba acotada
python scripts/bdd/poblar_fonetica.py --limit 1000

# Recalcular toda la fonética (p. ej. tras cambiar FONETICA_LANGUAGE)
python scripts/bdd/poblar_fonetica.py --force
```

Tras un `rebuild_nombres.py`, hay que volver a correr `poblar_fonetica.py` (la fonética se pierde al truncar la tabla).

---

## Decisiones de diseño

| Tema | Decisión |
|------|----------|
| Nombres compuestos en fuente | Se descomponen; el catálogo guarda solo tokens simples |
| Tildes | Se conservan; `JOSE` y `JOSÉ` son entradas distintas |
| Género | Dos filas M/F si aplica; no hay `U` |
| Fonética | Pre-procesada por nombre; apellidos se fonetizan en runtime al evaluar |
| Evaluación fonética | **Dos modos** (corto / completo) y **dos capas** (restricción / atracción); ver sección de criterios |
| Base de datos | SQLite en repo; PostgreSQL más adelante |
| Dialecto fonético | `es-419` por defecto (configurable en `phonemizer_config.py`) |

---

## Referencias bibliográficas y criterios de evaluación

Investigación previa al diseño del ranking fonético. No existe literatura que mida exactamente **nombre + dos apellidos**; lo más cercano es la eufonía **nombre + apellido**, complementada con fonotáctica, fonestética positiva y prosodia de frases.

El **modelo v2** (dos modos, dos capas, criterios A–Q) está implementado en `scripts/lib/fonetica_scoring.py`.

### Papers y fuentes consultadas

#### Eufonía nombre + apellido

| Referencia | URL | Conceptos que introduce |
|------------|-----|-------------------------|
| **Euphony in Polish combination of first and last names** (artículo académico, repositorio UZ Zielona Góra) | https://www.zbc.uz.zgora.pl/dlibra/publication/104676/edition/93276 | Define **eufonía** como evitar combinaciones difíciles de articular o desagradables al oído. Propone evitar: (1) **rimas** entre nombre y apellido; (2) **misma sílaba** al final del nombre y al inicio del apellido; (3) **imagen sonora muy parecida** entre ambos; (4) **gónicas o secuencias idénticas** en posiciones vecinas; (5) **grupos consonánticos** percibidos como difíciles. Cita la **ley de Behaghel**: combinaciones más eufónicas cuando el **primer elemento es más corto** (en sílabas) que el segundo. |
| **What is the secret to a nicely sounding name?** (corpus de registros civiles, Shropshire 2007) | https://www.grin.com/document/456246 | Analiza combinaciones reales nombre + apellido en inglés. Destaca **longitud y número de sílabas** equilibrados, **patrones de acento** (p. ej. 2+2 sílabas con acento trocaico), evitar **rima** y repetición de sonidos, y ajuste de **ritmo prosódico** entre nombre y apellido. No es español, pero los criterios son transferibles. |

#### Fonotáctica general (secuencias de sonidos)

| Referencia | URL | Conceptos que introduce |
|------------|-----|-------------------------|
| **Hayes & Wilson — Maximum Entropy Phonotactics** | https://linguistics.ucla.edu/people/wilson/HayesWilsonMaximumEntropyPhonotactics.pdf | Modelo clásico de **fonotáctica**: cada secuencia de fonemas tiene un score de **word-likeness** (qué tan probable suena en la lengua). Correlaciona con juicios humanos de bien formada. Aplicable a **uniones entre palabras**, no solo a palabras aisladas. |
| **UCI Phonotactic Calculator** | https://phonotactics.socsci.uci.edu/ | Herramienta online para calcular scores por **unigramas y bigramas** entrenados con un léxico. Permite evaluar la frecuencia de sonidos y pares adyacentes en una lengua concreta (p. ej. español). |

#### Unión entre palabras en español (juncture / sandhi)

| Referencia | URL | Conceptos que introduce |
|------------|-----|-------------------------|
| **External Vowel Sandhi in Castilian Spanish** (estudio reciente, PubMed) | https://pubmed.ncbi.nlm.nih.gov/41776154/ | Comportamiento de **vocales en frontera de palabra**: hiato, sandhi y resolución prosódica en español peninsular. |
| **Glottalizing at word junctures** (Cambridge Core, hablantes bilingües) | https://www.cambridge.org/core/journals/bilingualism-language-and-cognition/article/glottalizing-at-word-junctures-exploring-bidirectional-transfer-in-child-and-adult-spanish-heritage-speakers/A0EFAEBC7B352F8479AD79DCDA0F6622 | Junturas **consonante + vocal** entre palabras suelen fluir bien (resilabificación); junturas “duras” pueden percibirse peor. |
| **RAE — eufonía** | https://www.rae.es/dhle/eufon%C3%ADa | Alteración de formas para facilitar la pronunciación; base normativa del concepto en español. |
| **Wikilengua — Eufonía** | https://www.wikilengua.org/index.php/Eufon%C3%ADa | Proporción vocal/consonante, acentos, evitar **cacofonía** (secuencias repetidas o incómodas, p. ej. *colocolo*). |

#### Simbolismo sonoro (complemento, no core del ranking)

Estos estudios miden el **nombre aislado**, no la combinación nombre + apellidos. Útiles como capa secundaria o futura, no como sustituto del score de eufonía combinada.

| Referencia | URL | Conceptos que introduce |
|------------|-----|-------------------------|
| **Sidhu & Pexman (2019)** — *Current Directions in Psychological Science* | https://journals.sagepub.com/doi/10.1177/0963721419850134 | Sonidos “redondos” (/m/, /l/, /n/) vs “afilados” (/k/, /t/, /p/) y asociaciones de personalidad (efecto maluma/takete). |
| **Sound symbolism in first names** — *PLOS ONE* (2015) | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0126809 | Mismo efecto en nombres reales del inglés. |
| **University of Calgary — Baby naming** (divulgación) | https://news.ucalgary.ca/news/baby-naming-time-heres-how-people-judge-whats-name-1 | Resumen accesible del mecanismo de simbolismo sonoro en nombres. |

#### Fonestética y agrado positivo (palabras y frases)

Estudios sobre **“suena bien”**, no solo “evitar lo feo”. Base de la **capa de atracción** (criterios H–Q).

| Referencia | URL | Conceptos que introduce |
|------------|-----|-------------------------|
| **David Crystal — “Phonaesthetically Speaking”** | https://davidcrystal.com/Files/BooksAndArticles/-4009.pdf | Matriz de rasgos que **bonifican** palabras: sílabas múltiples, /l/ y sonorantes, balance vocal/consonante, distribución de sonidos. |
| **Reber, Schwarz & Winkielman — Processing Fluency and Aesthetic Pleasure** | https://pages.ucsd.edu/~pwinkiel/reber-schwarz-winkielman-beauty-PSPR-2004.pdf | Lo **fácil de procesar** se experimenta como agradable; prototipicidad y frecuencia → agrado. |
| **Frontiers 2025 — The phoenix of phonaesthetics** | https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1720029/full | Revisión: consonantes sonoras, prosodia fluida, regularidad silábica aumentan agrado. |
| **Obermeier et al. — Rhetorical features and prosodic fluency** | https://www.sciencedirect.com/science/article/pii/S0010027715300081 | **Metro, rima y brevedad** en frases facilitan fluidez prosódica y suben valor estético (matiz: en poesía la rima premia; en onomástica a menudo se penaliza). |
| **Reiterer & Kogan — Phon-aesthetic judgements of languages** | https://www.frontiersin.org/articles/10.3389/fnhum.2021.578594/pdf | **Sonoridad**, tempo y regularidad silábica influyen en juicios estéticos del habla. |

### Arquitectura del modelo de puntuación (v2)

Diseño acordado tras pruebas con `Ismael Tagle Díaz` y lote ergobaby (~186 nombres). Implementado en `scripts/lib/fonetica_scoring.py`.

#### Dos modos de evaluación

Los apellidos son **fijos** en una corrida; la unión `apellido1|apellido2` no discrimina entre nombres. Por eso se ofrecen **dos notas** para que el usuario elija qué priorizar:

| Modo | Frase evaluada | Para quién |
|------|----------------|------------|
| **Corto** | `nombre + apellido1` | Quien prioriza el primer apellido (uso diario, documentos informales) |
| **Completo** | `nombre + apellido1 + apellido2` | Quien quiere oír la identidad legal entera |

**Regla de uniones puntuadas**

| Criterio | Modo corto | Modo completo |
|----------|------------|---------------|
| A, B, C, D, G (frontera) | Solo unión `nombre\|apellido1` | Solo unión `nombre\|apellido1` — **no** puntuar `apellido1\|apellido2` |
| E (ritmo) | 2 piezas | 3 piezas (el 2.º apellido aporta longitud y acento) |
| F (Behaghel) | `sílabas(nombre)` vs `sílabas(apellido1)` | Igual, o vs bloque apellidos (a calibrar) |
| H–Q (atracción) | Según alcance de cada criterio | Idem; O (compacidad) usa la frase de 3 piezas |

Salida sugerida por candidato:

```
Ismael Tagle Díaz
  modo corto   → restriccion / atraccion / nota_final
  modo completo → restriccion / atraccion / nota_final
```

#### Dos capas: restricción vs atracción

| Capa | Pregunta | Lógica | Criterios |
|------|----------|--------|-----------|
| **Restricción** | ¿Suena mal o incómodo? | Partir de 100, **restar** penalizaciones | A–G |
| **Atracción** | ¿Suena fluido y agradable? | Partir de 50 (neutro), **sumar** bonificaciones hasta 100 | H–Q |

**Por qué dos capas:** la v1 (solo restricción) produce notas **demasiado altas y poco dispersas** (media ~91, σ ~4,4 en ergobaby vs Tagle Díaz): casi todo queda en 85–98 porque C, D y E suelen dar 100. La capa de atracción separa “aceptable” de “especialmente bonito”.

**Combinación de capas (orientativa)**

```
nota_final = 0,70 × nota_restriccion + 0,30 × nota_atraccion
```

Cada capa es a su vez un promedio ponderado de sus subcriterios (escala 0–100).

---

### Capa 1 — Restricción (criterios A–G)

Cada subcriterio produce **nota de 0 a 100** (100 = sin problemas bajo ese criterio). En v2, los criterios de **unión** (A, B, C, D, G) usan **solo** `nombre|apellido1`.

Entrada: fonética IPA del nombre (precomputada) + apellidos fonetizados en runtime (`scripts/lib/phonemizer_config.py`).

| ID | Criterio | Base teórica | Qué mide |
|----|----------|--------------|----------|
| **A** | Fonotáctica de unión (suelo) | Hayes & Wilson; UCI | Bigramas/trigramas raros en `nombre\|apellido1` → nota baja |
| **B** | Anti-rima / anti-asonancia | Artículo polaco; Shropshire | Coincidencia silábica/vocálica en la unión activa |
| **C** | Anti-repetición | Artículo polaco §2, §4 | Eco de sílaba o fonema en la unión activa |
| **D** | Anti-cluster / anti-cacofonía | Artículo polaco §5; Wikilengua | Clusters ilegales, pares raros, trigramas en percentil 1 |
| **E** | Anti-ritmo patológico | Shropshire | Desbalance silábico, acentos finales repetidos en todas las piezas del modo |
| **F** | Behaghel | Ley de Behaghel (polaco) | Nombre demasiado largo respecto al apellido1 |
| **G** | Sandhi mínimo | Juncture español | Tipo C+V / V+V / C+C en la unión activa |

#### Pesos capa restricción (orientativos)

| Criterio | Peso |
|----------|------|
| A | 25 % |
| B | 15 % |
| C | 15 % |
| D | 15 % |
| E | 15 % |
| F | 10 % |
| G | 5 % |

```
nota_restriccion = 0,25×A + 0,15×B + 0,15×C + 0,15×D + 0,15×E + 0,10×F + 0,05×G
```

#### Metodología capa restricción (0–100 por criterio)

**Origen:** solo **A** tiene método con validación empírica directa; **B–G** operacionalizan checklists de papers (umbrales heurísticos, calibrar con juicios manuales).

##### A — Fonotáctica de unión (suelo)

| Aspecto | Detalle |
|---------|---------|
| Unión | Solo `nombre\|apellido1` |
| Método | Tabla de bigramas desde el catálogo; ventana 2–4 fonemas en la unión; media de log-frecuencias; mapeo por percentiles (p5 → 0, p95 → 100) |

##### B — Anti-rima / anti-asonancia

| Escala en la unión activa | nota |
|---------------------------|------|
| Rima plena (núcleo + coda iguales) | 0 |
| Asonancia (mismas vocales en núcleo) | 40 |
| Coincidencia parcial de coda | 70 |
| Sin coincidencia relevante | 100 |

##### C — Anti-repetición

Partir de **100**; penalizaciones en la unión activa (mínimo 0):

| Detección | Penalización |
|-----------|--------------|
| Último fonema izq. = primer fonema der. | −50 |
| Última sílaba ≈ primera sílaba de la siguiente | −80 |
| ≥2 fonemas idénticos cruzando `\|` | 0 |

##### D — Anti-cluster / anti-cacofonía

Desde **100** en la unión activa: **−30** por violación dura (`#CC` ilegal, par raro `pt`/`mn`/…, misma consonante en `\|`); **−50** si trigrama de unión en percentil 1 del léxico.

##### E — Anti-ritmo patológico

`nota_E = 100 × (1 − penalización_normalizada)` con:

- distancia a plantillas silábicas del modo (corto: `(2,2)`, `(3,2)`…; completo: `(2,2,2)`, `(3,2,2)`…);
- penalización si nombre >> suma de sílabas de apellidos (solo modo completo);
- penalización si todas las piezas llevan acento en última sílaba.

##### F — Behaghel

`ratio = sílabas(nombre) / sílabas(apellido1)`:

| ratio | nota_F |
|-------|--------|
| ≤ 1,0 | 100 |
| 1,0 – 1,5 | 70 |
| 1,5 – 2,0 | 40 |
| > 2,0 | 20 |

Modo completo: **−15** si `sílabas(nombre) > sílabas(ap1) + sílabas(ap2)`.

##### G — Sandhi en unión activa

| Tipo en unión | nota |
|---------------|------|
| C+V | 100 |
| V+C | 90 |
| V+V distinto | 60 |
| V+V igual | 40 |
| C+C legal | 50 |
| C+C ilegal/raro | 10 |

---

### Capa 2 — Atracción (criterios H–Q)

Bonifican **fluidez, sonoridad y ritmo prototípico**. Escala **50 = neutro**, **100 = muy agradable**. Implementado en `scripts/lib/fonetica_scoring.py`.

| ID | Criterio | Paper | Medición | Bonificación (orientativa) |
|----|----------|-------|----------|----------------------------|
| **H** | Sonoridad segmental | Crystal; Reiterer | % fonemas sonoros en el nombre vs mediana del catálogo | 50–100 según ratio |
| **I** | Balance CV | Crystal; Wikilengua | `vocales/consonantes` del nombre en banda típica española (~0,8–1,4) | 50–100 |
| **J** | Perfil silábico del nombre | Crystal | 2–4 sílabas con acento primario claro | 50–65 |
| **K** | Fluidez fonotáctica (techo) | Reber et al.; Hayes | Log-bigramas de unión en percentil 75–95 (muy frecuentes) | 50–100 |
| **L** | Familiaridad del nombre | Reber (prototipicidad) | Frecuencia en catálogo/fuentes (requiere tabla stats) | +0–10 pts *(no implementado)* |
| **M** | Ritmo prototípico | Shropshire; Obermeier | Distancia mínima a plantillas favorables (bonus, no solo penalizar lejanía) | 50–100 |
| **N** | Agrupación prosódica | Prosody in reading | Compatibilidad acento nombre + apellidos del modo | 50–65 |
| **O** | Compacidad de frase | Obermeier (*brevitas*) | Total sílabas modo completo en banda 6–10 | 50–100 *(solo modo completo)* |
| **P** | Curva de sonoridad | Reiterer & Kogan | Sonoridad media de la frase; gesto prosódico coherente | 50–100 |
| **Q** | Suavidad en unión | Fonestética | Obstruyentes sordas en ventana ±2 fonemas de `\|` | 50–60 |
| **R** | Perfil maluma/takete *(opcional)* | Sidhu; PLOS ONE | Ratio sonorantes/oclusivas del nombre solo | Filtro de preferencia, fuera de nota global por defecto |

#### Pesos capa atracción (implementados)

| Criterio | Peso base | Notas |
|----------|-----------|-------|
| K — Fluidez fonotáctica | 25 % | Complemento positivo de A; misma unión `nombre\|apellido1` |
| M — Ritmo prototípico | 20 % | |
| H — Sonoridad | 15 % | |
| P — Curva de sonoridad | 10 % | |
| I — Balance CV | 10 % | |
| O — Compacidad | 10 % | Solo modo completo; excluido en corto (pesos renormalizados) |
| J, N, Q | ~3,3 % c/u | `1/30` cada uno |

```
nota_atraccion = promedio ponderado(H…Q)   # 50 = neutro; sin L ni R
nota_final     = 0,70 × nota_restriccion + 0,30 × nota_atraccion
```

#### Metodología capa atracción (0–100 por criterio)

**Origen:** igual que en restricción — **K** reutiliza el léxico fonotáctico de A con otro mapeo; **H–Q** operacionalizan rasgos de fonestética positiva con umbrales heurísticos (calibrar con juicios manuales).

**Alcance por modo**

| Criterio | Modo corto | Modo completo |
|----------|------------|---------------|
| H, I, J | Solo el **nombre** | Igual (heredado del corto) |
| K, Q | Unión `nombre\|apellido1` (núcleo compartido) | Igual |
| M, N, P | 2 piezas (`nombre`, `apellido1`) | 3 piezas (frase entera) |
| O | — | 3 piezas |

##### H — Sonoridad segmental (nombre)

| Aspecto | Detalle |
|---------|---------|
| Entrada | Tokens IPA del nombre |
| Ratio | `sonoros / total_fonemas`, donde sonoro = vocal o sonorante (`m`, `n`, `l`, `r`, `ɲ`, `ʎ`, `j`, `w`) |
| Referencia | Mediana del ratio calculada sobre todos los nombres del catálogo |
| Fórmula | `rel = ratio / mediana_catálogo`; mapeo lineal: `rel ≤ 0,85 → 50`, `rel ≥ 1,15 → 100`, interpolación entre ambos |

##### I — Balance CV (nombre)

| Aspecto | Detalle |
|---------|---------|
| Ratio | `vocales / consonantes` (sin marcas de acento) |
| Banda óptima | 0,8 – 1,4 (centro en 1,1) |
| En banda | `50 + 50 × (1 − |ratio − 1,1| / 0,3)` — máximo 100 en el centro |
| Fuera de banda | `50 − 15 × min(1, |ratio − 1,1| / 0,6)` |
| Sin consonantes | 65 fijo |

##### J — Perfil silábico (nombre)

| Condición | nota_J |
|-----------|--------|
| 2–3 sílabas con acento primario marcado | 65 |
| 4 sílabas con acento primario | 60 |
| 1 sílaba | 55 |
| Otros (sin acento o fuera de rango) | 50 |

##### K — Fluidez fonotáctica (techo)

| Aspecto | Detalle |
|---------|---------|
| Unión | Solo `nombre\|apellido1` (misma ventana de bigramas que A) |
| Método | Media de log-frecuencias de bigramas en la unión |
| Mapeo | Percentiles del léxico: **p75 → 50**, **p95 → 100** (complemento positivo de A, que usa p5–p95 hacia el suelo) |

##### M — Ritmo prototípico

Distancia mínima (L1 normalizada) entre el vector de sílabas por pieza y las plantillas favoritas del modo:

| Modo | Plantillas `(síl. nombre, síl. ap1, …)` |
|------|------------------------------------------|
| Corto | `(2,2)`, `(2,1)`, `(3,2)`, `(2,3)`, `(3,1)`, `(1,2)` |
| Completo | `(2,2,2)`, `(2,2,1)`, `(3,2,2)`, `(2,3,2)`, `(2,1,2)`, `(3,2,1)`, `(1,2,2)` |

```
dist = distancia_mínima / 4
nota_M = clamp(100 − dist × 50,  mínimo=50,  máximo=100)
```

A diferencia de **E** (penaliza lejanía desde 100), **M** bonifica proximidad desde un suelo de 50.

##### N — Agrupación prosódica

Partir de **50**; clasificar cada pieza como oxítona / paroxítona / proparoxítona según posición del acento primario:

| Patrón de acentos (nombre + apellidos del modo) | Bonificación |
|-------------------------------------------------|--------------|
| Nombre oxítono + resto paroxítonos | +15 |
| Todas paroxítonas | +10 |
| Mismo tipo en todas las piezas | +5 |
| Sin acento detectable en alguna pieza | 50 (neutro) |

##### O — Compacidad de frase *(solo modo completo)*

`total = sílabas(nombre) + sílabas(ap1) + sílabas(ap2)`

| total | nota_O |
|-------|--------|
| 6 – 10 | `50 + 50 × (1 − |total − 8| / 2)` — máximo 100 en total = 8 |
| Fuera de 6–10 | `50 − |total − 8| × 5` |

##### P — Curva de sonoridad (frase del modo)

| Aspecto | Detalle |
|---------|---------|
| Alcance | Corto: tokens de `nombre + apellido1`; completo: las 3 piezas |
| Escala por fonema | vocal 5, sonorante 4, sonora 2,5, obstruyente sorda 1, otro 2 |
| Fórmula | Media de sonoridad segmental; mapeo lineal **2,0 → 50**, **4,2 → 100** |

##### Q — Suavidad en unión

| Aspecto | Detalle |
|---------|---------|
| Unión | Solo `nombre\|apellido1` |
| Ventana | Últimos 2 fonemas del nombre + primeros 2 del apellido1 |
| Obstruyentes sordas | `p`, `t`, `k`, `f`, `s`, `θ`, `x`, `ʃ`, `ʧ` |
| Conteo | 0 sordas → 60; 1 → 55; ≥2 → `max(50, 60 − (n−1)×10)` |

**Nota:** Q varía poco cuando el apellido1 es fijo en una corrida (σ ≈ 2 en ergobaby vs Tagle Díaz); en la cruzada 10k con apellidos variados sube a σ ≈ 3.

##### L y R — no implementados

- **L** (familiaridad): requiere tabla de estadísticas por nombre; reservado para fase posterior.
- **R** (maluma/takete): capa opcional de preferencia personal; excluido de `nota_atraccion` por defecto.

**Tensión documentada:** la rima **premia** en poesía (Obermeier) pero **penaliza** en onomástica (polaco). No mezclar: anti-rima en capa 1 (B); ritmo/metro positivo en capa 2 (M, N) sin bonificar rima nombre–apellido.

---

### Resumen paper → criterio

| Criterio | ¿Fórmula en papers? | Capa | Origen escala |
|----------|---------------------|------|---------------|
| A | Sí | Restricción | Percentiles bigramas (suelo) |
| B–G | No (checklist) | Restricción | Penalizaciones / tablas |
| H–Q | Parcial | Atracción | Bonificaciones desde 50 |
| R | Parcial | Opcional | Preferencia personal |

---

### Estado de implementación

| Componente | Estado |
|------------|--------|
| `lib/fonetica_scoring.py` | **v2**: modos corto/completo, capas restricción + atracción (A–Q); núcleo compartido en unión `nombre\|apellido1` |
| `evaluacion/evaluar_combinacion.py` | Dos modos con desglose restricción / atracción |
| `evaluacion/evaluar_lote.py` | Lote con columnas `corto_*` y `completo_*` |

**Lección de la corrida ergobaby (v1):** media 91, mediana 91, rango 75,5–98,5 — poca utilidad discriminativa. Causas: techo alto por C/E/D casi siempre en 100; constante `apellido1\|apellido2` en el promedio de uniones.

---

### Validación prevista

1. Conjunto manual de 50–100 combinaciones calificadas (0–100) por un humano.
2. Calibrar pesos y umbrales (Spearman vs juicio humano) **por modo** y **por capa**.
3. Recentrar si hace falta (p. ej. mediana del lote ≈ 70) tras implementar v2.

#### Ejemplo: `Ismael Tagle Díaz`

Fonética (espeak `es-419`): `ˌismaˈel` + `tˈaɣle` + `dˈias`.

| Aspecto | Lectura |
|---------|---------|
| Unión activa `…el\|t…` | C+C (`l`+`t`) → G bajo en v1 |
| `Tagle\|Díaz` | V+C — **no debe puntuarse en v2** (constante para todos) |
| Modo corto | 2 piezas; foco en acople Ismael–Tagle |
| Modo completo | Ritmo 3+2+2; F con ratio 3/2 = 1,5 → 70 |

Corrida v1 (referencia, no objetivo v2): **nota_final ≈ 91,0** — ver `data/outputs/evaluacion_ismael_tagle_diaz.txt`.

#### Alcance y limitaciones

- Literatura directa: **nombre + un apellido**; extendemos a dos apellidos con reglas de unión explícitas.
- **No se evalúa** si Tagle y Díaz suenan bien **entre sí** en el ranking (apellidos fijos).
- Dialecto por defecto: **`es-419`** (latinoamericano). Cambiar a `es` implica `poblar_fonetica.py --force` y re-evaluar.
- Simbolismo sonoro (R): capa opcional, no sustituto de eufonía combinada.

---

## Próximos pasos

### Corto plazo

1. **Calibrar v2** contra juicios manuales (pesos, umbrales; objetivo mayor dispersión).
2. **Re-correr** ergobaby con `--modo-orden corto|completo` y revisar ranking.
3. **Refinar** criterios L (familiaridad) cuando exista tabla de estadísticas.

### Medio plazo

4. **Tabla de estadísticas** (frecuencia, país, año, edad media, fuente) referenciando `nombres.id` — habilita criterio L (familiaridad).
5. **Integrar fuentes restantes**: `bio-bio-2024.txt`, `ergobaby-2024.txt` en `nombres` (evaluación en lote ya usa ergobaby).
6. **`rank_nombres.py`**: ranking del catálogo completo dado par de apellidos + género, ordenable por modo y capa.

### Más adelante

7. **Validación manual** (50–100 combinaciones) y ajuste Spearman por capa/modo.
8. **Automatizar** fonética post-rebuild (opcional: un solo comando rebuild + fonetizar).
9. **Migración a PostgreSQL** cuando haga falta desplegar una app.
10. **UI o API** para consultar y rankear nombres (elección modo corto vs completo).

---

## Estructura del repositorio

```
seleccionador-nombres/
├── data/
│   ├── README.md
│   ├── raw/               # Descargas (CSV, XLSX, TXT, fuentes.txt)
│   ├── intermedio/        # Listas generadas (apellidos, pares)
│   ├── outputs/           # Resultados de evaluaciones
│   └── db/                # nombres.db
├── docs/
│   └── proyecto.md        # Este documento
├── schema/
│   ├── 001_nombres.sql
│   └── 002_fonetica.sql
├── scripts/               # Ver scripts/README.md
│   ├── lib/               # Módulos compartidos
│   ├── bdd/               # Pipeline base de datos
│   ├── evaluacion/        # Puntuación fonética
│   ├── setup/             # espeak-ng
│   ├── una_vez/           # Descarga / legacy
│   └── dev/               # Pruebas
├── vendor/espeak-ng/      # espeak-ng (gitignored, generado por setup)
├── requirements.txt
└── README.md
```

---

## Notas

- `vendor/espeak-ng/` y `.env` están en `.gitignore`.
- `docker-compose.yml` y `.env.example` existen por si más adelante se usa PostgreSQL; no son necesarios para el flujo SQLite actual.
