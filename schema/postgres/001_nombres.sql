CREATE TABLE IF NOT EXISTS nombres (
    id     SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    genero CHAR(1) NOT NULL CHECK (genero IN ('M', 'F')),
    UNIQUE (nombre, genero)
);

CREATE INDEX IF NOT EXISTS idx_nombres_nombre ON nombres (nombre);
CREATE INDEX IF NOT EXISTS idx_nombres_genero ON nombres (genero);
