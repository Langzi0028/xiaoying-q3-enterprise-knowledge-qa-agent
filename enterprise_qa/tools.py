"""Business tools with deterministic, safe outcomes."""

from __future__ import annotations

from pathlib import Path

from .knowledge_base import get_chunk, search_with_diagnostics
from .models import KnowledgeChunk, SearchResult, ToolOutcome


def search_documents(
    question: str, *, fail: bool = False, database: str | Path | None = None
) -> ToolOutcome[list[SearchResult]]:
    if fail:
        return ToolOutcome(ok=False, error_code="SEARCH_UNAVAILABLE")
    search = search_with_diagnostics(question, database=database)
    return ToolOutcome(
        ok=True,
        value=search.results,
        diagnostics={
            "retrieval_mode": search.mode,
            "cache_status": search.cache_status,
            "candidate_count": search.candidate_count,
            "selected_chunk_ids": [item.chunk_id for item in search.results],
            "selected_scores": search.selected_scores,
            "embedding_error_type": search.error_type,
        },
    )


def read_chunk(chunk_id: str, *, fail: bool = False) -> ToolOutcome[KnowledgeChunk]:
    if fail:
        return ToolOutcome(ok=False, error_code="READ_UNAVAILABLE")
    chunk = get_chunk(chunk_id)
    if chunk is None:
        return ToolOutcome(ok=False, error_code="CHUNK_NOT_FOUND")
    return ToolOutcome(ok=True, value=chunk)
