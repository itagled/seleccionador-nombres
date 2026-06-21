"""Cliente HTTP mínimo para chat completions (OpenRouter u OpenAI-compatible)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bootstrap import ROOT

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_S = 2.0

ENV_API_KEYS = ("OR_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str
    raw: dict[str, Any]


class LLMError(RuntimeError):
    pass


class LLMConfigError(LLMError):
    pass


def cargar_env(ruta: Path | None = None) -> None:
    """Carga variables desde .env si existen (sin pisar las ya definidas)."""
    if ruta is None:
        ruta = ROOT / ".env"
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        if clave and clave not in os.environ:
            os.environ[clave] = valor


def resolver_api_key(explicita: str | None = None) -> str:
    if explicita:
        return explicita.strip()
    for nombre in ENV_API_KEYS:
        if valor := os.environ.get(nombre, "").strip():
            return valor
    raise LLMConfigError(
        "Falta API key. Creá .env con OR_KEY=... (OpenRouter) "
        "o exportá OR_KEY / OPENROUTER_API_KEY."
    )


def resolver_base_url() -> str:
    return os.environ.get("OR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = 64,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_s: float = DEFAULT_RETRY_BACKOFF_S,
    referer: str | None = None,
    app_title: str | None = None,
) -> ChatResponse:
    """POST /chat/completions con reintentos en 429/5xx."""
    clave = resolver_api_key(api_key)
    url_base = (base_url or resolver_base_url()).rstrip("/")
    endpoint = f"{url_base}/chat/completions"

    cuerpo: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        cuerpo["max_tokens"] = max_tokens
    payload = json.dumps(cuerpo).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {clave}",
        "Content-Type": "application/json",
    }
    if referer or (referer := os.environ.get("OR_HTTP_REFERER")):
        headers["HTTP-Referer"] = referer
    if app_title or (app_title := os.environ.get("OR_APP_TITLE")):
        headers["X-Title"] = app_title

    ultimo_error: Exception | None = None
    for intento in range(max_retries):
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            cuerpo_err = exc.read().decode("utf-8", errors="replace")
            ultimo_error = LLMError(f"HTTP {exc.code}: {cuerpo_err[:500]}")
            if exc.code in (429, 500, 502, 503, 504) and intento + 1 < max_retries:
                time.sleep(retry_backoff_s * (intento + 1))
                continue
            raise ultimo_error from exc
        except urllib.error.URLError as exc:
            ultimo_error = LLMError(str(exc))
            if intento + 1 < max_retries:
                time.sleep(retry_backoff_s * (intento + 1))
                continue
            raise ultimo_error from exc
    else:
        raise ultimo_error or LLMError("Sin respuesta del LLM")

    try:
        contenido = raw["choices"][0]["message"]["content"]
        if contenido is None:
            msg = raw["choices"][0]["message"]
            contenido = msg.get("reasoning") or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Respuesta inesperada: {raw!r}") from exc

    if not str(contenido).strip():
        raise LLMError(f"Respuesta vacía: {raw!r}")

    modelo_resp = str(raw.get("model") or model)
    return ChatResponse(content=str(contenido).strip(), model=modelo_resp, raw=raw)
