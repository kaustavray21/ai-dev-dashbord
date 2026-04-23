"""
openai_client.py — Concrete OpenAI client satisfying IOpenAIClient.

Features:
  • Loads api_key and model from Django settings (never hard-coded).
  • chat_completion  — base chat call, optional tool definitions.
  • embed_text       — single-text embedding via text-embedding-3-small.
  • embed_batch      — batch embedding (Phase 2 scaffold).
  • Retry logic      — catches RateLimitError, backs off 2 s / 4 s / 8 s
                       for up to 3 attempts.
  • Token logging    — every successful response logs tokens_used at DEBUG
                       level so we can track costs without exposing data.
"""

from __future__ import annotations

import logging
import time

import openai
from django.conf import settings

from services.contracts import IOpenAIClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_BACKOFF_SECONDS = [2, 4, 8]          # wait time before each retry attempt
_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIClient:
    """
    Concrete implementation of IOpenAIClient backed by the official OpenAI
    Python SDK (openai >= 1.0).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Initialise the client.

        api_key  — defaults to settings.OPENAI_API_KEY
        model    — defaults to settings.OPENAI_MODEL (typically 'gpt-4o')
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o")
        self._client = openai.OpenAI(api_key=self.api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(self, fn, *args, **kwargs):
        """
        Call *fn* with retry logic.  Catches openai.RateLimitError and
        backs off exponentially.  Re-raises on all other exceptions.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return fn(*args, **kwargs)
            except openai.RateLimitError as exc:
                last_exc = exc
                wait = _BACKOFF_SECONDS[attempt] if attempt < len(_BACKOFF_SECONDS) else 8
                logger.warning(
                    "OpenAI RateLimitError (attempt %d/%d). Retrying in %ds…",
                    attempt + 1,
                    _MAX_RETRIES,
                    wait,
                )
                time.sleep(wait)
        # All retries exhausted — raise the last captured exception
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API  (satisfies IOpenAIClient protocol)
    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> dict:
        """
        Send a chat-completion request to OpenAI.

        Parameters
        ----------
        messages : list[dict]
            Standard OpenAI messages array (role / content dicts).
        tools : list[dict] | None
            Optional tool / function definitions for tool-calling (Phase 2).
        stream : bool
            Not yet implemented — reserved for Phase 3 SSE streaming.

        Returns
        -------
        dict
            {
                "content":     str,   # assistant reply text
                "tokens_used": int,   # total_tokens from usage
                "raw":         obj,   # raw SDK response object
            }
        """
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        def _do_call():
            return self._client.chat.completions.create(**kwargs)

        response = self._call_with_retry(_do_call)

        content = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.debug(
            "chat_completion OK | model=%s tokens_used=%d",
            self.model,
            tokens_used,
        )

        return {
            "content": content,
            "tokens_used": tokens_used,
            "raw": response,
        }

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single string using text-embedding-3-small.

        Returns a list[float] (the embedding vector).
        """
        def _do_call():
            return self._client.embeddings.create(
                model=_EMBEDDING_MODEL,
                input=text,
            )

        response = self._call_with_retry(_do_call)
        vector = response.data[0].embedding

        logger.debug(
            "embed_text OK | model=%s vector_dim=%d",
            _EMBEDDING_MODEL,
            len(vector),
        )

        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of strings in a single API call.

        Returns a list of embedding vectors ordered to match *texts*.
        Phase 2 scaffold — wire up to vector store on demand.
        """
        if not texts:
            return []

        def _do_call():
            return self._client.embeddings.create(
                model=_EMBEDDING_MODEL,
                input=texts,
            )

        response = self._call_with_retry(_do_call)

        # SDK returns items in the same order as input
        vectors = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]

        logger.debug(
            "embed_batch OK | model=%s batch_size=%d vector_dim=%d",
            _EMBEDDING_MODEL,
            len(texts),
            len(vectors[0]) if vectors else 0,
        )

        return vectors


# ---------------------------------------------------------------------------
# Protocol compliance check (runs at import time in DEBUG, cheap assertion)
# ---------------------------------------------------------------------------
assert isinstance(OpenAIClient, type)          # sanity
assert issubclass(OpenAIClient, object)        # always true — real check below

def _verify_protocol() -> None:
    """Raise TypeError at startup if OpenAIClient drifts from IOpenAIClient."""
    from services.contracts import IOpenAIClient as _P
    dummy = OpenAIClient.__new__(OpenAIClient)
    if not isinstance(dummy, _P):              # runtime_checkable Protocol
        raise TypeError(
            "OpenAIClient no longer satisfies IOpenAIClient — "
            "check that all protocol methods are implemented."
        )

_verify_protocol()
