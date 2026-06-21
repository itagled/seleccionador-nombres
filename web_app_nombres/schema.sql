-- Comparador pairwise T2 (recolección humana web)

CREATE TABLE IF NOT EXISTS pares (
    id          SERIAL PRIMARY KEY,
    tipo        VARCHAR(2) NOT NULL,
    genero      CHAR(1) NOT NULL CHECK (genero IN ('M', 'F')),
    apellido1   VARCHAR(255) NOT NULL,
    apellido2   VARCHAR(255),
    nombre_a    VARCHAR(255) NOT NULL,
    nombre_b    VARCHAR(255) NOT NULL,
    forma_a     VARCHAR(512) NOT NULL,
    forma_b     VARCHAR(512) NOT NULL,
    estrategia  VARCHAR(32),
    activo      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS votos (
    id          SERIAL PRIMARY KEY,
    par_id      INTEGER NOT NULL REFERENCES pares (id) ON DELETE CASCADE,
    ganador     CHAR(1) NOT NULL CHECK (ganador IN ('A', 'B')),
    session_id  UUID NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (par_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_pares_tipo ON pares (tipo);
CREATE INDEX IF NOT EXISTS idx_pares_activo ON pares (activo);
CREATE INDEX IF NOT EXISTS idx_votos_session ON votos (session_id);
CREATE INDEX IF NOT EXISTS idx_votos_par ON votos (par_id);
