"""
contracts.py — Protocol interfaces for the services layer.

All service callers depend on these abstractions (not concrete classes),
enabling easy swapping, mocking, and testing of AI back-ends.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IOpenAIClient(Protocol):
    """
    Ground-truth interface for any OpenAI-compatible client.

    Concrete implementations (OpenAIClient, MockOpenAIClient, …) must
    satisfy every method defined here.  Use @runtime_checkable so
    callers can do  isinstance(client, IOpenAIClient)  in tests.
    """

    def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> dict:
        """
        Send a chat request and return a normalised response dict.

        Return shape:
            {
                "content":     str,          # assistant text
                "tokens_used": int,          # total tokens consumed
                "raw":         object,       # raw openai response (optional)
            }
        """
        ...

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single piece of text using text-embedding-3-small.

        Returns a list of floats (the embedding vector).
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts in a single API call.

        Returns a list of embedding vectors (one per input text).
        Scaffold for Phase 2 — vector search.
        """
        ...
