"""LLM access.

Like embeddings and the vector store, the chat model sits behind a Protocol so
the RAG orchestrator never imports OpenAI directly. `complete` is used for
one-shot generation (summaries, quizzes, query rewriting); `stream` yields text
deltas for the chat endpoint's server-sent events.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


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


class OpenAILLMProvider:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env to call the LLM."
            )
        from openai import OpenAI

        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        self.model = settings.llm_model

    def _messages(self, system: str, user: str) -> list[dict]:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def complete(self, system, user, *, temperature=None, json_mode=False) -> str:
        kwargs: dict = {
            "model": self.model,
            "messages": self._messages(system, user),
            "temperature": settings.llm_temperature if temperature is None else temperature,
            "max_tokens": settings.llm_max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def stream(self, system, user, *, temperature=None) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=self._messages(system, user),
            temperature=settings.llm_temperature if temperature is None else temperature,
            max_tokens=settings.llm_max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if settings.llm_provider == "openai":
            _provider = OpenAILLMProvider()
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
