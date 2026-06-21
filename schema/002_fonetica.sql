-- Migracion SQLite: agrega columna fonetica a nombres existentes.
-- Idempotente: SQLite no permite IF NOT EXISTS en ADD COLUMN; el script
-- poblar_fonetica.py comprueba antes de ejecutar esto.

ALTER TABLE nombres ADD COLUMN fonetica TEXT;
