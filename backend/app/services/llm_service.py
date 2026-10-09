"""LLM access.

The chat model sits behind a Protocol so RAG code does not know which local
runtime serves tokens. `complete` is used for summaries, quizzes, and query
rewrites; `stream` yields text deltas for server-sent events.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)

_NO_REASONING_INSTRUCTION = (
    "Do not output hidden reasoning, chain-of-thought, or <think> blocks. "
    "Return only the final answer requested by the user."
)
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


class LLMProvider(Protocol):
    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> str:
        ...

    def stream(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
    ) -> Iterator[str]:
        ...


class LLMError(RuntimeError):
    """User-facing LLM failure."""


class OllamaLLMProvider:
    """Local chat model served by Ollama."""

    def __init__(self) -> None:
        self.model = settings.llm_model

    def _messages(self, system: str, user: str) -> list[dict]:
        system = f"{system.rstrip()}\n\n{_NO_REASONING_INSTRUCTION}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _payload(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        json_mode: bool = False,
        stream: bool = False,
    ) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": self._messages(system, user),
            "stream": stream,
            "options": {
                "temperature": settings.llm_temperature
                if temperature is None
                else temperature,
                "num_predict": settings.llm_max_tokens,
            },
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    def complete(self, system, user, *, temperature=None, json_mode=False) -> str:
        from app.services.ollama_client import OllamaError, post_json

        try:
            resp = post_json(
                "/api/chat",
                self._payload(
                    system,
                    user,
                    temperature=temperature,
                    json_mode=json_mode,
                ),
                model=self.model,
            )
            content = resp.get("message", {}).get("content", "")
            if not isinstance(content, str):
                raise LLMError("Ollama returned an unexpected chat response.")
            return strip_think_blocks(content)
        except OllamaError as exc:
            raise LLMError(str(exc)) from exc

    def stream(self, system, user, *, temperature=None) -> Iterator[str]:
        from app.services.ollama_client import OllamaError, stream_json_lines

        try:
            filter_state = _ThinkStreamFilter()
            for item in stream_json_lines(
                "/api/chat",
                self._payload(system, user, temperature=temperature, stream=True),
                model=self.model,
            ):
                delta = item.get("message", {}).get("content")
                if delta:
                    cleaned = filter_state.feed(delta)
                    if cleaned:
                        yield cleaned
                if item.get("done"):
                    break
            tail = filter_state.flush()
            if tail:
                yield tail
        except OllamaError as exc:
            raise LLMError(str(exc)) from exc




_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if settings.llm_provider == "ollama":
            _provider = OllamaLLMProvider()
        else:  # pragma: no cover
            raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
    return _provider


def set_llm_provider(provider: LLMProvider) -> None:
    """DI hook for tests."""
    global _provider
    _provider = provider


def parse_json_response(raw: str) -> dict | list:
    """Best-effort JSON parse that tolerates accidental markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        # drop a leading language hint like "json\n"
        if "\n" in text:
            text = text.split("\n", 1)[1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fall back to extracting the outermost JSON object/array.
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise


def strip_think_blocks(text: str) -> str:
    """Remove reasoning blocks some local instruct models emit by default."""
    return _THINK_BLOCK_RE.sub("", text).strip()


class _ThinkStreamFilter:
    """Incrementally suppress <think>...</think> spans from streamed chunks."""

    def __init__(self) -> None:
        self._buffer = ""
        self._inside_think = False

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        out: list[str] = []

        while self._buffer:
            lowered = self._buffer.lower()
            if self._inside_think:
                end = lowered.find("</think>")
                if end == -1:
                    keep = min(len(self._buffer), len("</think>") - 1)
                    self._buffer = self._buffer[-keep:] if keep else ""
                    return "".join(out)
                self._buffer = self._buffer[end + len("</think>") :]
                self._inside_think = False
                continue

            start = lowered.find("<think>")
            partial = _partial_tag_prefix(self._buffer, "<think>")
            emit_until = len(self._buffer) - partial
            if start == -1 or start >= emit_until:
                if emit_until > 0:
                    out.append(self._buffer[:emit_until])
                    self._buffer = self._buffer[emit_until:]
                return "".join(out)

            out.append(self._buffer[:start])
            self._buffer = self._buffer[start + len("<think>") :]
            self._inside_think = True

        return "".join(out)

    def flush(self) -> str:
        if self._inside_think:
            self._buffer = ""
            return ""
        tail = self._buffer
        self._buffer = ""
        return tail


def _partial_tag_prefix(text: str, tag: str) -> int:
    max_len = min(len(text), len(tag) - 1)
    lowered = text.lower()
    for size in range(max_len, 0, -1):
        if tag.startswith(lowered[-size:]):
            return size
    return 0
