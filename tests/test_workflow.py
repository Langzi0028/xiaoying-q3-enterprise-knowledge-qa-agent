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


def test_conflict_is_not_hidden_by_an_extra_retrieval_candidate(tmp_path: Path) -> None:
    from enterprise_qa.models import KnowledgeChunk
    from enterprise_qa.tools import ToolOutcome
    from enterprise_qa.workflow import execute_action

    # The final Agent guard must key off D01/D02 presence, not an exact set.
    state = {
        "read_chunks": [
            KnowledgeChunk("D01", "Travel", "2026.1", "2026-01-01", "D01-C1", "30 days"),
            KnowledgeChunk("D02", "Urgent", "2026.2", "2026-02-15", "D02-C1", "15 days"),
            KnowledgeChunk("P01", "Export", "2026.1", "2026-01-10", "P01-C1", "30 days"),
        ],
        "trace": [],
        "decision": type("Decision", (), {"action": "answer_with_citations", "source": "live_llm", "rationale": "test"})(),
        "steps": 0,
        "max_steps": 8,
        "fail_tool": None,
        "fail_consumed": False,
        "storage": type("Storage", (), {"checkpoint": lambda *args: None})(),
        "run_id": "test",
    }

    completed = execute_action(state)

    assert completed["result"].status == "clarification_required"
    assert {item["document_id"] for item in completed["result"].citations} == {
        "D01",
        "D02",
    }


def test_model_selected_chunk_id_controls_the_first_read(tmp_path: Path) -> None:
    from enterprise_qa.planner import Planner

    result = run_question(
        "报销凭证多久提交？",
        database=tmp_path / "q3.db",
        planner=Planner.with_test_response({"action": "read_chunk", "chunk_id": "D02-C1"}),
    )

    reads = [item for item in result.trace if item["action"] == "read_chunk"]

    assert reads[0]["parameters"]["chunk_id"] == "D02-C1"
    assert reads[0]["decision_source"] == "live_llm"
    assert reads[0]["parameters"]["model_selected_chunk"] is True
    assert "D02-C1" in reads[0]["parameters"]["candidate_chunk_ids"]


def test_model_stop_before_evidence_returns_explicitly_incomplete(tmp_path: Path) -> None:
    from enterprise_qa.planner import Planner

    result = run_question(
        "普通国内差旅报销凭证多久提交？",
        database=tmp_path / "q3.db",
        planner=Planner.with_test_response({"action": "stop"}),
    )

    assert result.status == "incomplete"
    assert result.error_code == "MODEL_STOPPED_BEFORE_EVIDENCE"
