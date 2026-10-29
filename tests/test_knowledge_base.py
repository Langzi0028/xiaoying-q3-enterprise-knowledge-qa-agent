from enterprise_qa.knowledge_base import search_documents
from enterprise_qa.tools import read_chunk


def test_search_returns_both_conflicting_expense_documents() -> None:
    results = search_documents("报销凭证多久提交？")

    assert {result.document_id for result in results} == {"D01", "D02"}


def test_search_normalizes_domestic_travel_reformulation() -> None:
    results = search_documents("国内出差的发票最迟几天交？")

    assert [result.document_id for result in results] == ["D01"]


def test_read_chunk_returns_versioned_primary_source_text() -> None:
    outcome = read_chunk("D01-C1")

    assert outcome.ok is True
    assert outcome.value.document_id == "D01"
    assert outcome.value.version == "2026.1"
    assert "30" in outcome.value.text
