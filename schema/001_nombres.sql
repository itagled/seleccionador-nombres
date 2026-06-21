CREATE TABLE IF NOT EXISTS nombres (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre   TEXT NOT NULL,
    genero   TEXT NOT NULL CHECK (genero IN ('M', 'F')),
    fonetica TEXT,
    UNIQUE (nombre, genero)
);

CREATE INDEX IF NOT EXISTS idx_nombres_nombre ON nombres (nombre);
CREATE INDEX IF NOT EXISTS idx_nombres_genero ON nombres (genero);
