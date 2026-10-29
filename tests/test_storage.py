from pathlib import Path

from enterprise_qa.storage import Storage


FINAL_RESULT = {"status": "answered", "answer": "30 days"}
TRACE = [{"action": "search_documents", "parameters": {"question_length": 8}}]


def test_run_persists_redacted_trace_and_final_result(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "audit.db")

    storage.record_run("run-1", FINAL_RESULT, TRACE)

    saved = storage.get_run("run-1")
    assert saved is not None
    assert saved["final_result"]["status"] == "answered"
    assert saved["trace"][0]["action"] == "search_documents"


def test_conversation_context_returns_only_previous_safe_subject(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "audit.db")

    storage.save_conversation_subject("conv-1", "reimbursement")

    assert storage.get_conversation_subject("conv-1") == "reimbursement"
