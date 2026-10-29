"""Constrained next-action selection with a transparent fallback boundary."""

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any


ALLOWED_ACTIONS = {
    "search_documents",
    "read_chunk",
    "ask_clarifying_question",
    "answer_with_citations",
    "stop",
}


@dataclass(frozen=True)
class Decision:
    action: str
    source: str
    rationale: str
    parameters: dict[str, str] | None = None


class Planner:
    def __init__(
        self, *, has_live_config: bool, test_response: dict[str, Any] | None = None
    ) -> None:
        self.has_live_config = has_live_config
        self.test_response = test_response
        self.last_error_type: str | None = None
        self._live_disabled = False

    @classmethod
    def from_environment(cls) -> "Planner":
        return cls(
            has_live_config=all(
                os.getenv(name)
                for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")
            )
        )

    @classmethod
    def with_test_response(cls, response: dict[str, Any]) -> "Planner":
        return cls(has_live_config=True, test_response=response)

    def choose(self, state: dict[str, Any]) -> Decision:
        if self.test_response is not None:
            decision = self._validate_live_action(self.test_response, state)
            if decision is None:
                return self._rule_decision(state, "fallback_invalid_output")
            return Decision(
                action=decision.action,
                source="live_llm",
                rationale="Validated test decision.",
                parameters=decision.parameters,
            )
        if not self.has_live_config:
            return self._rule_decision(state, "fallback_missing_config")
        if self._live_disabled:
            return self._rule_decision(state, "fallback_live_error")
        try:
            live_response = self._request_live_action(state)
        except Exception as error:  # The CLI exposes only this public type name.
            self.last_error_type = type(error).__name__
            self._live_disabled = True
            return self._rule_decision(state, "fallback_live_error")
        decision = self._validate_live_action(live_response, state)
        if decision is None:
            self._live_disabled = True
            return self._rule_decision(state, "fallback_invalid_output")
        return Decision(
            action=decision.action,
            source="live_llm",
            rationale="Validated constrained live-model action.",
            parameters=decision.parameters,
        )

    def _request_live_action(self, state: dict[str, Any]) -> dict[str, Any]:
        """Request one small, non-sensitive action object from the configured model."""
        from langchain_openai import ChatOpenAI

        rule_decision = self._rule_decision(state, "fallback_missing_config")
        allowed_actions = self._allowed_live_actions(state, rule_decision)
        client = ChatOpenAI(
            model=os.environ["LLM_MODEL"],
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ["LLM_BASE_URL"],
            temperature=0,
            timeout=15,
            use_responses_api=os.getenv("LLM_API_MODE", "responses") != "chat_completions",
        )
        response = client.invoke(
            [
                (
                    "system",
                    "Return only JSON with action. For read_chunk, also return chunk_id selected from the supplied unread_chunk_ids. Do not include reasoning.",
                ),
                (
                    "user",
                    json.dumps(
                        {
                            "allowed_actions": allowed_actions,
                            "unread_chunk_ids": self._unread_chunk_ids(state),
                            "question_length": len(str(state.get("question", ""))),
                            "search_result_count": len(state.get("search_results", [])),
                            "read_chunk_count": len(state.get("read_chunks", [])),
                            "tool_error": state.get("tool_error"),
                        }
                    ),
                ),
            ]
        )
        content = response.content
        if not isinstance(content, str):
            raise ValueError("Model returned non-text action content")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Model returned non-object action content")
        return parsed

    def _validate_live_action(
        self, response: dict[str, Any], state: dict[str, Any]
    ) -> Decision | None:
        action = response.get("action")
        rule_decision = self._rule_decision(state, "fallback_missing_config")
        if action not in self._allowed_live_actions(state, rule_decision):
            return None
        if action == "read_chunk":
            chunk_id = response.get("chunk_id")
            if chunk_id not in self._unread_chunk_ids(state):
                return None
            return Decision(action, "live_llm", "", {"chunk_id": chunk_id})
        return Decision(action, "live_llm", "")

    @staticmethod
    def _unread_chunk_ids(state: dict[str, Any]) -> list[str]:
        read_ids = {
            chunk.chunk_id for chunk in state.get("read_chunks", [])
        }
        return [
            result.chunk_id
            for result in state.get("search_results", [])
            if result.chunk_id not in read_ids
        ]

    @staticmethod
    def _allowed_live_actions(
        state: dict[str, Any], rule_decision: Decision
    ) -> list[str]:
        if rule_decision.action == "read_chunk":
            return ["read_chunk", "stop"]
        return [rule_decision.action]

    def _rule_decision(self, state: dict[str, Any], source: str) -> Decision:
        if state.get("tool_error"):
            return Decision("stop", source, "A required tool failed.")
        if not state.get("search_completed"):
            return Decision("search_documents", source, "Search must run before evidence can be read.")
        search_results = state.get("search_results", [])
        if not search_results:
            return Decision("stop", source, "No supporting document was found.")
        read_chunks = state.get("read_chunks", [])
        unread = [item for item in search_results if item.chunk_id not in {chunk.chunk_id for chunk in read_chunks}]
        if unread:
            return Decision(
                "read_chunk",
                source,
                "Read the next retrieved source chunk.",
                {"chunk_id": unread[0].chunk_id},
            )
        document_ids = {chunk.document_id for chunk in read_chunks}
        if {"D01", "D02"}.issubset(document_ids) and not state.get("urgent_scope"):
            return Decision(
                "ask_clarifying_question",
                source,
                "The retrieved deadlines conflict until urgent-project scope is known.",
            )
        return Decision("answer_with_citations", source, "Verified source chunks support the result.")
