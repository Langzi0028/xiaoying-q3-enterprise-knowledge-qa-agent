"""Safe synthetic enterprise documents and deterministic retrieval."""

from __future__ import annotations

from .models import KnowledgeChunk, SearchResult


_CHUNKS = (
    KnowledgeChunk(
        document_id="D01",
        title="Travel and Expense Policy",
        version="2026.1",
        date="2026-01-01",
        chunk_id="D01-C1",
        text="普通国内差旅报销凭证须在费用发生后 30 个自然日内提交。",
    ),
    KnowledgeChunk(
        document_id="D02",
        title="Urgent Project Expense Addendum",
        version="2026.2",
        date="2026-02-15",
        chunk_id="D02-C1",
        text="紧急项目报销凭证须在费用发生后 15 个自然日内提交。适用前须确认该费用属于紧急项目。",
    ),
    KnowledgeChunk(
        document_id="P01",
        title="Creator Hub Export Guide",
        version="2026.1",
        date="2026-01-10",
        chunk_id="P01-C1",
        text="导出的视频片段在 Creator Hub 中自生成起保留 30 天。",
    ),
)


def _matches_expense(query: str) -> bool:
    return any(token in query for token in ("报销", "凭证", "发票", "费用"))


def _matches_urgent(query: str) -> bool:
    return "紧急项目" in query or ("紧急" in query and "项目" in query)


def _matches_domestic_travel(query: str) -> bool:
    return any(token in query for token in ("国内", "出差", "差旅", "普通"))


def search_documents(question: str) -> list[SearchResult]:
    """Return only safe metadata for chunks relevant to the question."""
    normalized = question.strip()
    selected: list[KnowledgeChunk] = []
    if _matches_expense(normalized):
        if _matches_urgent(normalized):
            selected = [_CHUNKS[1]]
        elif _matches_domestic_travel(normalized):
            selected = [_CHUNKS[0]]
        else:
            selected = [_CHUNKS[0], _CHUNKS[1]]
    elif any(token in normalized.lower() for token in ("export", "导出", "剪辑")):
        selected = [_CHUNKS[2]]
    return [
        SearchResult(
            document_id=item.document_id,
            title=item.title,
            version=item.version,
            date=item.date,
            chunk_id=item.chunk_id,
            excerpt=item.text[:96],
        )
        for item in selected
    ]


def get_chunk(chunk_id: str) -> KnowledgeChunk | None:
    return next((item for item in _CHUNKS if item.chunk_id == chunk_id), None)
