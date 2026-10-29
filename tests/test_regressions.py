from pathlib import Path

from enterprise_qa.planner import Planner
from enterprise_qa.workflow import run_question


def test_unrelated_question_reports_not_found(tmp_path: Path) -> None:
    result = run_question("公司股票什么时候上市？", database=tmp_path / "q3.db")

    assert result.status == "not_found"
    assert result.answer is not None
    assert result.citations == []


def test_reformulated_question_still_returns_d01(tmp_path: Path) -> None:
    result = run_question("国内出差的发票最迟几天交？", database=tmp_path / "q3.db")

    assert result.status == "answered"
    assert result.citations[0]["document_id"] == "D01"


def test_follow_up_question_uses_safe_conversation_subject(tmp_path: Path) -> None:
    database = tmp_path / "q3.db"
    run_question("普通差旅报销的期限？", database=database, conversation_id="c1")

    result = run_question("那紧急项目呢？", database=database, conversation_id="c1")

    assert result.status == "answered"
    assert result.citations[0]["document_id"] == "D02"


def test_search_failure_is_safe_and_does_not_claim_an_answer(tmp_path: Path) -> None:
    result = run_question(
        "报销凭证多久提交？",
        database=tmp_path / "q3.db",
        fail_tool="search_documents",
    )

    assert result.status == "tool_failed"
    assert result.answer is None
    assert result.error_code == "SEARCH_UNAVAILABLE"


def test_read_failure_is_safe_and_is_not_retried_indefinitely(tmp_path: Path) -> None:
    result = run_question(
        "普通国内差旅报销凭证多久提交？",
        database=tmp_path / "q3.db",
        fail_tool="read_chunk",
    )

    reads = [item for item in result.trace if item["action"] == "read_chunk"]
    assert result.status == "tool_failed"
    assert result.answer is None
    assert len(reads) == 1
    assert reads[0]["result_summary"] == "Chunk read failed with READ_UNAVAILABLE."


def test_empty_question_returns_invalid_request_without_tool_trace(tmp_path: Path) -> None:
    result = run_question("   ", database=tmp_path / "q3.db")

    assert result.status == "invalid_request"
    assert result.trace == []
    assert result.error_code == "QUESTION_REQUIRED"


def test_invalid_live_model_action_falls_back_and_cannot_skip_evidence(tmp_path: Path) -> None:
    result = run_question(
        "普通国内差旅报销凭证多久提交？",
        database=tmp_path / "q3.db",
        planner=Planner.with_test_response({"action": "delete_database"}),
    )

    assert result.status == "answered"
    assert result.decision_source == "fallback_invalid_output"
    assert any(item["action"] == "read_chunk" for item in result.trace)
