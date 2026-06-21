# Comparador web — recolección humana

Web app mínima (FastAPI + PostgreSQL) para comparar pares T2 (`Nombre A Apellido` vs `Nombre B Apellido`) y guardar votos anónimos por sesión.

## Endpoints

| Método | Ruta | Uso |
|--------|------|-----|
| `GET` | `/` | UI del comparador |
| `GET` | `/health` | Health check (Render) |
| `GET` | `/api/par` | Siguiente par no votado en esta sesión |
| `POST` | `/api/voto` | Body JSON: `{"par_id": 1, "ganador": "A"}` |
| `GET` | `/api/progreso` | `{votados, total}` de la sesión |

Al arrancar, la app crea las tablas y carga **500 pares T2** desde `data/intermedio/pilot_pares.csv` si la tabla `pares` está vacía.

---

## Desarrollo local

### 1. Base PostgreSQL

Con Docker (desde la raíz del repo):

```bash
docker compose up -d
```

### 2. Variable de entorno

Creá `web_app_nombres/.env` (opcional) o exportá en la terminal:

```bash
# Windows PowerShell
$env:DATABASE_URL = "postgresql://seleccionador:seleccionador@localhost:5432/seleccionador_nombres"
```

En Linux/macOS:

```bash
export DATABASE_URL="postgresql://seleccionador:seleccionador@localhost:5432/seleccionador_nombres"
```

> Render entrega la URL como `postgres://...`; la app la normaliza a `postgresql://` automáticamente.

### 3. Instalar y correr

```bash
cd web_app_nombres
pip install -r requirements.txt
python seed.py          # opcional; el arranque también siembra si hace falta
uvicorn main:app --reload --port 8000
```

Abrí http://127.0.0.1:8000

---

## Deploy en Render (sin dominio propio)

Obtenés una URL pública tipo `https://comparador-nombres.onrender.com`.

### Opción A — Blueprint (`render.yaml` en la raíz del repo)

1. Subí el repo a GitHub (si aún no está).
2. En [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Conectá el repo `seleccionador-nombres`.
4. Render lee `render.yaml` y propone:
   - **Web Service** `comparador-nombres` (carpeta `web_app_nombres`)
   - **PostgreSQL** `comparador-nombres-db`
5. Confirmá el deploy. Render vincula `DATABASE_URL` solo.

### Opción B — Manual (más control)

#### Paso 1: Crear PostgreSQL

1. **New** → **PostgreSQL**.
2. Nombre ej. `comparador-nombres-db`.
3. Región: la misma que usarás para la web.
4. Plan: el más barato disponible (Render ya no ofrece Postgres gratis permanente; revisá precios actuales).
5. Al crear, copiá **Internal Database URL** o **External Database URL**.

#### Paso 2: Crear Web Service

1. **New** → **Web Service** → conectá el repo.
2. Configuración:

| Campo | Valor |
|-------|-------|
| **Root Directory** | `web_app_nombres` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |

3. **Environment** → agregar variable:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Pegá la **External Database URL** de Render (formato `postgres://user:pass@host/db`) |

   Alternativa: en el Web Service → **Connect** → **Add database** → elegí la Postgres creada; Render inyecta `DATABASE_URL` automáticamente.

4. **Deploy**.

#### Paso 3: Verificar seed

Tras el primer deploy exitoso:

- Visitá `/health` → `{"status":"ok"}`
- Visitá `/` → deberías ver pares
- En los logs del servicio: `Comparador listo: 500 pares T2 disponibles.`

Si la base estaba vacía, el startup ejecuta schema + seed.

---

## Dónde va `DATABASE_URL`

| Entorno | Dónde |
|---------|--------|
| **Render (producción)** | Dashboard → tu Web Service → **Environment** → `DATABASE_URL`. Mejor vincular la DB con **Add database** para que Render la mantenga. |
| **Local** | Terminal (`export` / `$env:`) o archivo `.env` en `web_app_nombres/` (gitignored si lo creás vos). |
| **No commitear** | Nunca subas la URL con password al repo. |

Otras variables: ninguna obligatoria para la web. (`OR_KEY` del LLM es solo para scripts offline.)

---

## Exportar votos

Desde el shell de Render (PostgreSQL → **Connect** → **PSQL**) o cualquier cliente:

```sql
SELECT
    p.tipo,
    p.genero,
    p.apellido1,
    p.nombre_a,
    p.nombre_b,
    p.forma_a,
    p.forma_b,
    p.estrategia,
    v.ganador,
    v.session_id,
    v.created_at
FROM votos v
JOIN pares p ON p.id = v.par_id
ORDER BY v.created_at;
```

Para CSV compatible con el pipeline offline, mapeá `ganador` → columna del ganador (A/B) y `fuente = 'humano_web'`.

---

## Notas

- **Free tier web:** la app se duerme tras inactividad; el primer acceso puede tardar ~30 s.
- **Un voto por par y sesión:** cookie `sn_session` (anónima, 1 año).
- **Sin login:** cualquiera con el link puede votar; no compartas el link públicamente si querés limitar audiencia.
- **Recargar pares:** vaciá `votos` y/o `pares` en SQL y redeploy, o ejecutá `python seed.py` tras truncar `pares`.
