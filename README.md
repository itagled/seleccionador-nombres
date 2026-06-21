# seleccionador-nombres

Base de datos de nombres de habla hispana y herramientas para recomendar nombres según afinidad fonética con los apellidos del bebé.

## Estado

- **Base de datos:** SQLite (`data/db/nombres.db`), tabla `nombres` con ~215k entradas (`nombre`, `genero`, `fonetica`).
- **Fuentes integradas:** España 2012 (CSV), Chile guaguas (CSV), España 2025 (XLSX).
- **Fonética:** phonemizer + espeak-ng; columna `fonetica` en migración / población parcial.

Documentación completa, decisiones de diseño y próximos pasos:

**[docs/proyecto.md](docs/proyecto.md)**

## Inicio rápido

```bash
pip install -r requirements.txt
python scripts/setup/setup_espeak.py
python scripts/bdd/rebuild_nombres.py
python scripts/bdd/poblar_fonetica.py
```
