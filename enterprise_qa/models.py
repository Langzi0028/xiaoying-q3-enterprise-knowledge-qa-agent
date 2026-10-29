"""Small, safe data structures shared by the agent modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    title: str
    version: str
    date: str
    chunk_id: str
    excerpt: str


@dataclass(frozen=True)
class KnowledgeChunk:
    document_id: str
    title: str
    version: str
    date: str
    chunk_id: str
    text: str


@dataclass(frozen=True)
class ToolOutcome(Generic[T]):
    ok: bool
    value: T | None = None
    error_code: str | None = None


@dataclass
class FinalResult:
    status: str
    answer: str | None
    clarifying_question: str | None
    citations: list[dict[str, str]]
    decision_source: str
    trace: list[dict[str, object]]
    error_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "answer": self.answer,
            "clarifying_question": self.clarifying_question,
            "citations": self.citations,
            "decision_source": self.decision_source,
            "trace": self.trace,
            "error_code": self.error_code,
        }
