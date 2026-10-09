"""Tiny Ollama HTTP client used by the local LLM provider and health checks."""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib import error, request

from app.config import settings


class OllamaError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _url(path: str) -> str:
    return settings.ollama_base_url.rstrip("/") + path


def _json_request(path: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    return request.Request(
        _url(path),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )


def _friendly_error(exc: Exception, *, model: str) -> OllamaError:
    if isinstance(exc, error.HTTPError):
        try:
            details = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            details = ""
        if exc.code == 404:
            return OllamaError(
                f"Ollama model '{model}' is not installed. Run: ollama pull {model}",
                status_code=exc.code,
            )
        lowered = details.lower()
        if "memory" in lowered or "out of memory" in lowered:
            return OllamaError(
                "Ollama could not load the model because there is not enough RAM. "
                "Try a smaller model, for example qwen3:4b.",
                status_code=exc.code,
            )
        suffix = f" Details: {details}" if details else ""
        return OllamaError(
            f"Ollama returned HTTP {exc.code}.{suffix}", status_code=exc.code
        )
    if isinstance(exc, error.URLError):
        return OllamaError(
            "Local AI provider is unavailable. Install/start Ollama and make sure "
            f"the configured model is installed: ollama pull {model}"
        )
    return OllamaError(str(exc))


def get_json(path: str, *, model: str) -> dict:
    try:
        with request.urlopen(  # noqa: S310 - local/user-configured Ollama URL
            _url(path),
            timeout=settings.ollama_timeout_seconds,
        ) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise _friendly_error(exc, model=model) from exc


def post_json(path: str, payload: dict, *, model: str) -> dict:
    try:
        with request.urlopen(  # noqa: S310 - local/user-configured Ollama URL
            _json_request(path, payload),
            timeout=settings.ollama_timeout_seconds,
        ) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise _friendly_error(exc, model=model) from exc


def stream_json_lines(path: str, payload: dict, *, model: str) -> Iterator[dict]:
    try:
        with request.urlopen(  # noqa: S310 - local/user-configured Ollama URL
            _json_request(path, payload),
            timeout=settings.ollama_timeout_seconds,
        ) as resp:
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if line:
                    yield json.loads(line)
    except Exception as exc:  # noqa: BLE001
        raise _friendly_error(exc, model=model) from exc


def probe_ollama(model: str) -> dict:
    """Return a small health payload without invoking generation."""
    try:
        data = get_json("/api/tags", model=model)
    except OllamaError as exc:
        return {
            "provider": "ollama",
            "model": model,
            "status": "unavailable",
            "message": str(exc),
        }

    installed = {
        value
        for item in data.get("models", [])
        for value in (item.get("name"), item.get("model"))
        if value
    }
    if model not in installed:
        return {
            "provider": "ollama",
            "model": model,
            "status": "model_missing",
            "message": f"Ollama is running, but '{model}' is not installed. Run: ollama pull {model}",
        }
    return {
        "provider": "ollama",
        "model": model,
        "status": "connected",
        "message": "Ollama is running and the configured model is installed.",
    }
