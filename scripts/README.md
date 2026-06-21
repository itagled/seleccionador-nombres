# Scripts

Utilidades del proyecto agrupadas por función. Los módulos compartidos viven en `lib/` (no ejecutar directamente).

## Estructura

```
scripts/
├── lib/              Módulos importables (fonética, fuentes, puntuación)
├── bdd/              Pipeline de base de datos — uso recurrente
├── evaluacion/       Puntuación fonética nombre + apellidos — uso recurrente
├── setup/            Configuración del entorno — ocasional
├── una_vez/          Descarga/import legacy — uso puntual
└── dev/              Pruebas y muestras — desarrollo
```

## Uso recurrente

### Base de datos (`bdd/`)

| Script | Comando | Descripción |
|--------|---------|-------------|
| `rebuild_nombres.py` | `python scripts/bdd/rebuild_nombres.py` | Reconstruye `nombres` desde todas las fuentes |
| `import_nombres.py` | `python scripts/bdd/import_nombres.py` | Atajo → `rebuild_nombres.py` |
| `poblar_fonetica.py` | `python scripts/bdd/poblar_fonetica.py` | Rellena columna `fonetica` |

Tras un rebuild hay que volver a ejecutar `poblar_fonetica.py`.

### Evaluación fonética (`evaluacion/`)

| Script | Comando | Descripción |
|--------|---------|-------------|
| `evaluar_combinacion.py` | `python scripts/evaluacion/evaluar_combinacion.py --nombre X --apellido1 Y --apellido2 Z` | Una combinación con desglose A–G |
| `evaluar_lote.py` | `python scripts/evaluacion/evaluar_lote.py` | Lote (p. ej. ergobaby) vs apellidos fijos |

### Setup (`setup/`)

| Script | Cuándo |
|--------|--------|
| `setup_espeak.py` | Primera vez o si falta `vendor/espeak-ng/` |
| `install_espeak_windows.ps1` | Alternativa: instalar espeak-ng en el sistema (Windows) |

## Uso puntual (`una_vez/`)

| Script | Descripción |
|--------|-------------|
| `download_guaguas.py` | Descarga guaguas desde CRAN → `data/raw/guaguas.csv` (ya ejecutado) |
| `import_guaguas_nombres.py` | Import incremental solo guaguas — **legacy**; preferir `bdd/rebuild_nombres.py` |

## Desarrollo (`dev/`)

| Script | Descripción |
|--------|-------------|
| `muestra_fonetica.py` | Genera `data/outputs/muestra_fonetica_100.csv` para inspección |

## Módulos (`lib/`)

| Módulo | Función |
|--------|---------|
| `bootstrap.py` | Rutas del repo e import de `lib/` |
| `phonemizer_config.py` | espeak-ng + `fonetizar_texto()` |
| `nombres_sources.py` | Lectura y normalización de fuentes CSV/XLSX |
| `fonetica_scoring.py` | Lógica de puntuación (criterios A–G; v1) |

## Flujo habitual

```bash
pip install -r requirements.txt
python scripts/setup/setup_espeak.py
python scripts/bdd/rebuild_nombres.py
python scripts/bdd/poblar_fonetica.py
python scripts/evaluacion/evaluar_combinacion.py --nombre Ismael --apellido1 Tagle --apellido2 Díaz --genero M
```
