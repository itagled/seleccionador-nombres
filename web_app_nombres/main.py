"""Comparador de nombres — web app para recolección humana (Render)."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Literal

from pydantic import BaseModel, Field

from db import ensure_schema, obtener_siguiente_par, progreso_sesion, registrar_voto
from seed import seed_if_empty

SESSION_COOKIE = "sn_session"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_schema()
    n = seed_if_empty()
    print(f"Comparador listo: {n} pares T2 disponibles.")
    yield


app = FastAPI(title="Comparador de nombres", lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


class VotoIn(BaseModel):
    par_id: int = Field(..., ge=1)
    ganador: Literal["A", "B"]


def _parse_session(raw: str | None, response: Response) -> UUID:
    if raw:
        try:
            return UUID(raw)
        except ValueError:
            pass
    session_id = uuid.uuid4()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=str(session_id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 365,
    )
    return session_id


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/api/progreso")
def api_progreso(
    response: Response,
    sn_session: str | None = Cookie(default=None),
) -> dict[str, int]:
    session_id = _parse_session(sn_session, response)
    return progreso_sesion(session_id)


@app.get("/api/par")
def api_par(
    response: Response,
    sn_session: str | None = Cookie(default=None),
) -> dict:
    session_id = _parse_session(sn_session, response)
    par = obtener_siguiente_par(session_id)
    prog = progreso_sesion(session_id)
    if par is None:
        return {"par": None, **prog}
    genero_txt = "niña" if par["genero"] == "F" else "niño"
    return {
        "par": {
            "id": par["id"],
            "forma_a": par["forma_a"],
            "forma_b": par["forma_b"],
            "genero": genero_txt,
            "apellido1": par["apellido1"],
        },
        **prog,
    }


@app.post("/api/voto")
def api_voto(
    body: VotoIn,
    response: Response,
    sn_session: str | None = Cookie(default=None),
) -> dict[str, bool | dict[str, int]]:
    session_id = _parse_session(sn_session, response)
    ok = registrar_voto(par_id=body.par_id, ganador=body.ganador, session_id=session_id)
    if not ok:
        raise HTTPException(status_code=409, detail="Ya votaste este par.")
    return {"ok": True, "progreso": progreso_sesion(session_id)}
