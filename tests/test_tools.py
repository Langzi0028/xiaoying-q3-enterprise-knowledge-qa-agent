from enterprise_qa.tools import read_chunk, search_documents


def test_search_tool_exposes_a_safe_failure_result() -> None:
    outcome = search_documents("报销凭证多久提交？", fail=True)

    assert outcome.ok is False
    assert outcome.error_code == "SEARCH_UNAVAILABLE"
    assert outcome.value is None


def test_chunk_tool_exposes_a_safe_failure_result() -> None:
    outcome = read_chunk("D01-C1", fail=True)

    assert outcome.ok is False
    assert outcome.error_code == "READ_UNAVAILABLE"
    assert outcome.value is None
