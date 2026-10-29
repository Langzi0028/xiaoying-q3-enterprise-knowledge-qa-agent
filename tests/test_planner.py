from enterprise_qa.planner import ALLOWED_ACTIONS, Planner


class SearchResult:
    def __init__(self, chunk_id: str) -> None:
        self.chunk_id = chunk_id


def test_missing_config_uses_explicit_rule_fallback(monkeypatch) -> None:
    for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)

    decision = Planner.from_environment().choose({"search_results": [], "read_chunks": []})

    assert decision.source == "fallback_missing_config"
    assert decision.action == "search_documents"


def test_invalid_live_action_is_rejected_and_falls_back() -> None:
    decision = Planner.with_test_response({"action": "delete_database"}).choose(
        {"search_results": [], "read_chunks": []}
    )

    assert decision.source == "fallback_invalid_output"
    assert decision.action in ALLOWED_ACTIONS


def test_live_model_can_choose_one_safe_unread_source_chunk() -> None:
    state = {
        "search_completed": True,
        "search_results": [SearchResult("D01-C1"), SearchResult("D02-C1")],
        "read_chunks": [],
    }

    decision = Planner.with_test_response(
        {"action": "read_chunk", "chunk_id": "D02-C1"}
    ).choose(state)

    assert decision.source == "live_llm"
    assert decision.action == "read_chunk"
    assert decision.parameters == {"chunk_id": "D02-C1"}


def test_invalid_live_chunk_choice_uses_safe_fallback_target() -> None:
    state = {
        "search_completed": True,
        "search_results": [SearchResult("D01-C1"), SearchResult("D02-C1")],
        "read_chunks": [],
    }

    decision = Planner.with_test_response(
        {"action": "read_chunk", "chunk_id": "NOT-A-SOURCE"}
    ).choose(state)

    assert decision.source == "fallback_invalid_output"
    assert decision.action == "read_chunk"
    assert decision.parameters == {"chunk_id": "D01-C1"}


def test_live_model_may_safely_stop_while_sources_remain_unread() -> None:
    state = {
        "search_completed": True,
        "search_results": [SearchResult("D01-C1")],
        "read_chunks": [],
    }

    decision = Planner.with_test_response({"action": "stop"}).choose(state)

    assert decision.source == "live_llm"
    assert decision.action == "stop"
