"""Cached cosine retrieval over local document chunk embeddings."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .chunking import chunk_fingerprint, embedding_text
from .embeddings import EmbeddingProvider
from .models import KnowledgeChunk, SearchResult


@dataclass(frozen=True)
class VectorSearch:
    results: list[SearchResult]
    mode: str
    cache_status: str
    candidate_count: int
    selected_scores: dict[str, float]
    error_type: str | None = None


# A lower-scoring document must remain close to the leading document before
# diversity can add it. This avoids turning an explicit policy scope into a
# false conflict while still preserving genuinely close competing policies.
_DIVERSITY_SCORE_RATIO = 0.8
_LIVE_MIN_RELEVANCE_SCORE = 0.5
_HASH_MIN_RELEVANCE_SCORE = 0.1


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left or not right:
        return -1.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else -1.0


class VectorIndex:
    def __init__(self, database: str | Path, provider: EmbeddingProvider) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self._initialize()

    @classmethod
    def with_hash_fallback(
        cls, database: str | Path, *, model_name: str = "local-feature-hash-v4"
    ) -> "VectorIndex":
        return cls(database, EmbeddingProvider.hash_fallback(model_name=model_name))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS embedding_index_metadata (
                    corpus_fingerprint TEXT NOT NULL,
                    embedding_fingerprint TEXT NOT NULL,
                    vector_dimension INTEGER NOT NULL,
                    PRIMARY KEY (corpus_fingerprint, embedding_fingerprint)
                );
                CREATE TABLE IF NOT EXISTS embedding_vectors (
                    corpus_fingerprint TEXT NOT NULL,
                    embedding_fingerprint TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    PRIMARY KEY (corpus_fingerprint, embedding_fingerprint, chunk_id)
                );
                """
            )

    def search(
        self, question: str, chunks: list[KnowledgeChunk], *, top_k: int = 3
    ) -> VectorSearch:
        corpus_key = chunk_fingerprint(chunks)
        query_batch = self.provider.embed([question])
        effective_provider = (
            self.provider
            if query_batch.mode == "live_embedding"
            else EmbeddingProvider.hash_fallback(model_name=query_batch.model_name)
        )
        embedding_key = effective_provider.fingerprint
        vectors, cache_status, chunk_error = self._chunk_vectors(
            corpus_key, embedding_key, chunks, effective_provider
        )
        query_vector = query_batch.vectors[0]
        error_type = query_batch.error_type or chunk_error
        if chunk_error and effective_provider.mode == "live_embedding":
            effective_provider = EmbeddingProvider.hash_fallback()
            embedding_key = effective_provider.fingerprint
            query_batch = effective_provider.embed([question])
            query_vector = query_batch.vectors[0]
            vectors, cache_status, _ = self._chunk_vectors(
                corpus_key, embedding_key, chunks, effective_provider
            )
        if not vectors or len(next(iter(vectors.values()))) != len(query_vector):
            fallback_provider = EmbeddingProvider.hash_fallback()
            vectors = fallback_provider.embed([embedding_text(chunk) for chunk in chunks]).vectors
            vectors = {chunk.chunk_id: vector for chunk, vector in zip(chunks, vectors)}
            query_vector = fallback_provider.embed([question]).vectors[0]
            cache_status = "cache_rebuilt"
            error_type = error_type or "ValueError"

        ranked = sorted(
            ((chunk, _cosine(query_vector, vectors[chunk.chunk_id])) for chunk in chunks),
            key=lambda item: item[1],
            reverse=True,
        )
        scope_is_explicit = any(
            token in question for token in ("普通", "国内", "出差", "差旅", "紧急项目")
        )
        leading_score = ranked[0][1] if ranked else 0.0
        diversity_floor = (
            max(0.0, leading_score * _DIVERSITY_SCORE_RATIO)
            if scope_is_explicit
            else 0.0
        )
        selected = self._diverse_selection(ranked, top_k, diversity_floor=diversity_floor)
        relevance_floor = (
            _LIVE_MIN_RELEVANCE_SCORE
            if query_batch.mode == "live_embedding" and not error_type
            else _HASH_MIN_RELEVANCE_SCORE
        )
        result_items = [
            SearchResult(
                document_id=chunk.document_id,
                title=chunk.title,
                version=chunk.version,
                date=chunk.date,
                chunk_id=chunk.chunk_id,
                excerpt=chunk.text[:96],
                retrieval_score=round(score, 4),
            )
            for chunk, score in selected
            if score >= relevance_floor
        ]
        return VectorSearch(
            results=result_items,
            mode=query_batch.mode if not error_type else "hash_fallback",
            cache_status=cache_status,
            candidate_count=len(chunks),
            selected_scores={item.chunk_id: float(item.retrieval_score or 0.0) for item in result_items},
            error_type=error_type,
        )

    def _chunk_vectors(
        self,
        corpus_key: str,
        embedding_key: str,
        chunks: list[KnowledgeChunk],
        provider: EmbeddingProvider,
    ) -> tuple[dict[str, list[float]], str, str | None]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT chunk_id, vector_json FROM embedding_vectors "
                "WHERE corpus_fingerprint = ? AND embedding_fingerprint = ?",
                (corpus_key, embedding_key),
            ).fetchall()
        expected = {chunk.chunk_id for chunk in chunks}
        cached = {chunk_id: json.loads(vector) for chunk_id, vector in rows}
        if set(cached) == expected and cached:
            dimensions = {len(vector) for vector in cached.values()}
            if len(dimensions) == 1:
                return cached, "cache_hit", None

        batch = provider.embed([embedding_text(chunk) for chunk in chunks])
        if batch.error_type:
            return {}, "cache_rebuilt", batch.error_type
        generated = {chunk.chunk_id: vector for chunk, vector in zip(chunks, batch.vectors)}
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM embedding_vectors WHERE corpus_fingerprint = ? AND embedding_fingerprint = ?",
                (corpus_key, embedding_key),
            )
            connection.executemany(
                "INSERT INTO embedding_vectors (corpus_fingerprint, embedding_fingerprint, chunk_id, vector_json) VALUES (?, ?, ?, ?)",
                [
                    (corpus_key, embedding_key, chunk_id, json.dumps(vector))
                    for chunk_id, vector in generated.items()
                ],
            )
            connection.execute(
                "INSERT OR REPLACE INTO embedding_index_metadata (corpus_fingerprint, embedding_fingerprint, vector_dimension) VALUES (?, ?, ?)",
                (corpus_key, embedding_key, len(batch.vectors[0]) if batch.vectors else 0),
            )
        return generated, "cache_rebuilt", batch.error_type

    @staticmethod
    def _diverse_selection(
        ranked: list[tuple[KnowledgeChunk, float]], top_k: int, diversity_floor: float
    ) -> list[tuple[KnowledgeChunk, float]]:
        selected: list[tuple[KnowledgeChunk, float]] = []
        seen_documents: set[str] = set()
        for chunk, score in ranked:
            if chunk.document_id not in seen_documents and score >= diversity_floor:
                selected.append((chunk, score))
                seen_documents.add(chunk.document_id)
            if len(selected) >= top_k:
                return selected
        if not selected and ranked:
            selected.append(ranked[0])
        return selected
