from enterprise_qa.planner import ALLOWED_ACTIONS, Planner


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
