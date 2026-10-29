from pathlib import Path

from enterprise_qa.workflow import run_question


def test_clear_question_answers_only_with_a_chunk_read_in_this_run(tmp_path: Path) -> None:
    result = run_question("普通国内差旅报销凭证多久提交？", database=tmp_path / "q3.db")

    assert result.status == "answered"
    assert result.citations[0]["document_id"] == "D01"
    assert any(item["action"] == "read_chunk" for item in result.trace)
    assert result.trace[-1]["next_action"] == "finalize"


def test_conflicting_deadlines_require_scope_clarification(tmp_path: Path) -> None:
    result = run_question("报销凭证多久提交？", database=tmp_path / "q3.db")

    assert result.status == "clarification_required"
    assert result.answer is None
    assert {item["document_id"] for item in result.citations} == {"D01", "D02"}
    assert "紧急项目" in result.clarifying_question


def test_limit_exhaustion_is_explicitly_incomplete(tmp_path: Path) -> None:
    result = run_question("报销凭证多久提交？", database=tmp_path / "q3.db", max_steps=1)

    assert result.status == "incomplete"
    assert result.error_code == "EXECUTION_LIMIT_REACHED"


def test_search_trace_contains_safe_embedding_diagnostics(tmp_path: Path) -> None:
    result = run_question("报销凭证多久提交？", database=tmp_path / "q3.db")

    search = next(item for item in result.trace if item["action"] == "search_documents")

    assert search["parameters"]["retrieval_mode"] == "hash_fallback"
    assert search["parameters"]["candidate_count"] >= 2
    assert "vector" not in str(search["parameters"]).lower()
