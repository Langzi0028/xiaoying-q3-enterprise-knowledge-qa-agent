"""Clause-aware chunks that keep policy requirements and scope together."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

from .corpus import SourceDocument
from .models import KnowledgeChunk


CLAUSE_BRIDGE_VERSION = "clause-bridge-v1"
_SENTENCE_PATTERN = re.compile(r"(?<=。)")
_ANCHOR_TERMS = ("期限", "须", "必须", "适用", "例外", "确认要求", "不得")


def _sentences(body: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_PATTERN.split(body) if part.strip()]


def _chunk_id(document: SourceDocument, ordinal: int) -> str:
    return f"{document.document_id}-C{ordinal}"


def build_chunks(documents: Iterable[SourceDocument]) -> list[KnowledgeChunk]:
    """Build stable policy chunks around obligations and their scope clauses."""
    chunks: list[KnowledgeChunk] = []
    for document in documents:
        sentences = _sentences(document.body)
        emitted: set[str] = set()
        ordinal = 1
        for index, sentence in enumerate(sentences):
            if not any(term in sentence for term in _ANCHOR_TERMS):
                continue
            start = max(0, index - 1)
            end = min(len(sentences), index + 2)
            text = "".join(sentences[start:end])
            if text in emitted:
                continue
            emitted.add(text)
            chunks.append(
                KnowledgeChunk(
                    document_id=document.document_id,
                    title=document.title,
                    version=document.version,
                    date=document.date,
                    chunk_id=_chunk_id(document, ordinal),
                    text=text,
                )
            )
            ordinal += 1
        if not emitted:
            chunks.append(
                KnowledgeChunk(
                    document_id=document.document_id,
                    title=document.title,
                    version=document.version,
                    date=document.date,
                    chunk_id=_chunk_id(document, ordinal),
                    text=document.body,
                )
            )
    return chunks


def embedding_text(chunk: KnowledgeChunk) -> str:
    return f"{chunk.title}\n版本 {chunk.version}\n日期 {chunk.date}\n{chunk.text}"


def corpus_fingerprint(documents: Iterable[SourceDocument]) -> str:
    serializable = [
        {
            "document_id": item.document_id,
            "title": item.title,
            "version": item.version,
            "date": item.date,
            "body": item.body,
        }
        for item in documents
    ]
    payload = json.dumps(
        {"version": CLAUSE_BRIDGE_VERSION, "documents": serializable},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunk_fingerprint(chunks: Iterable[KnowledgeChunk]) -> str:
    payload = json.dumps(
        {
            "version": CLAUSE_BRIDGE_VERSION,
            "chunks": [
                {
                    "document_id": chunk.document_id,
                    "version": chunk.version,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                }
                for chunk in chunks
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
