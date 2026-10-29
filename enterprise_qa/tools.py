"""Business tools with deterministic, safe outcomes."""

from __future__ import annotations

from .knowledge_base import get_chunk, search_documents as search
from .models import KnowledgeChunk, SearchResult, ToolOutcome


def search_documents(question: str, *, fail: bool = False) -> ToolOutcome[list[SearchResult]]:
    if fail:
        return ToolOutcome(ok=False, error_code="SEARCH_UNAVAILABLE")
    return ToolOutcome(ok=True, value=search(question))


def read_chunk(chunk_id: str, *, fail: bool = False) -> ToolOutcome[KnowledgeChunk]:
    if fail:
        return ToolOutcome(ok=False, error_code="READ_UNAVAILABLE")
    chunk = get_chunk(chunk_id)
    if chunk is None:
        return ToolOutcome(ok=False, error_code="CHUNK_NOT_FOUND")
    return ToolOutcome(ok=True, value=chunk)
