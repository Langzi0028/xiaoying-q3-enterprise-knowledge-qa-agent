"""Embedding retrieval facade over locally generated policy chunks."""

from __future__ import annotations

from pathlib import Path

from .chunking import build_chunks
from .corpus import DOCUMENTS
from .embeddings import EmbeddingProvider
from .models import KnowledgeChunk, SearchResult
from .vector_index import VectorIndex, VectorSearch


_CHUNKS = build_chunks(DOCUMENTS)
_DEFAULT_INDEX_DATABASE = Path("data") / "embedding_index.db"


def search_with_diagnostics(
    question: str, *, database: str | Path | None = None
) -> VectorSearch:
    index = VectorIndex(
        database or _DEFAULT_INDEX_DATABASE,
        EmbeddingProvider.from_environment(),
    )
    return index.search(question.strip(), _CHUNKS, top_k=3)


def search_documents(question: str) -> list[SearchResult]:
    """Return safe search results; diagnostics are available to the tool layer."""
    return search_with_diagnostics(question).results


def get_chunk(chunk_id: str) -> KnowledgeChunk | None:
    return next((item for item in _CHUNKS if item.chunk_id == chunk_id), None)
