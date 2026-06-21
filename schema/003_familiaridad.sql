CREATE TABLE IF NOT EXISTS familiaridad (
    nombre_id          INTEGER PRIMARY KEY REFERENCES nombres (id) ON DELETE CASCADE,
    prevalencia        REAL NOT NULL DEFAULT 0,
    log_familiaridad   REAL NOT NULL,
    prop_reciente      REAL
);

CREATE INDEX IF NOT EXISTS idx_familiaridad_log ON familiaridad (log_familiaridad);
