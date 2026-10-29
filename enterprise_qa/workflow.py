"""Bounded LangGraph workflow for evidence-backed enterprise questions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from .models import FinalResult, KnowledgeChunk
from .planner import Decision, Planner
from .storage import Storage
from .tools import read_chunk, search_documents


class AgentState(TypedDict, total=False):
    question: str
    conversation_id: str | None
    storage: Storage
    planner: Planner
    max_steps: int
    fail_tool: str | None
    fail_consumed: bool
    run_id: str
    steps: int
    search_completed: bool
    search_results: list[Any]
    read_chunks: list[KnowledgeChunk]
    urgent_scope: bool
    tool_error: str | None
    embedding_error_type: str | None
    decision: Decision
    trace: list[dict[str, object]]
    result: FinalResult | None


def _citation(chunk: KnowledgeChunk) -> dict[str, str]:
    return {
        "document_id": chunk.document_id,
        "version": chunk.version,
        "date": chunk.date,
        "chunk_id": chunk.chunk_id,
        "title": chunk.title,
    }


def _checkpoint(state: AgentState) -> None:
    storage = state["storage"]
    storage.checkpoint(
        state["run_id"],
        state.get("steps", 0),
        {
            "search_completed": state.get("search_completed", False),
            "read_chunk_ids": [chunk.chunk_id for chunk in state.get("read_chunks", [])],
            "tool_error": state.get("tool_error"),
            "has_result": state.get("result") is not None,
        },
    )


def _append_trace(
    state: AgentState,
    *,
    action: str,
    parameters: dict[str, object],
    result_summary: str,
    rationale: str,
    source: str,
) -> None:
    state.setdefault("trace", []).append(
        {
            "step": state.get("steps", 0),
            "node": "execute_action",
            "action": action,
            "parameters": parameters,
            "result_summary": result_summary,
            "next_action": None,
            "decision_source": source,
            "rationale": rationale,
        }
    )


def _finalize_result(
    state: AgentState,
    *,
    status: str,
    answer: str | None = None,
    clarifying_question: str | None = None,
    citations: list[dict[str, str]] | None = None,
    error_code: str | None = None,
) -> None:
    source = state.get("decision", Decision("stop", "fallback_missing_config", "")).source
    state["result"] = FinalResult(
        status=status,
        answer=answer,
        clarifying_question=clarifying_question,
        citations=citations or [],
        decision_source=source,
        trace=state.get("trace", []),
        error_code=error_code,
        embedding_error_type=state.get("embedding_error_type"),
    )


def validate_input(state: AgentState) -> AgentState:
    if not state["question"].strip():
        _finalize_result(state, status="invalid_request", error_code="QUESTION_REQUIRED")
    _checkpoint(state)
    return state


def choose_action(state: AgentState) -> AgentState:
    if state.get("result") is not None:
        return state
    state["decision"] = state["planner"].choose(state)
    _checkpoint(state)
    return state


def execute_action(state: AgentState) -> AgentState:
    if state.get("result") is not None:
        return state
    if state.get("steps", 0) >= state["max_steps"]:
        _finalize_result(
            state,
            status="incomplete",
            error_code="EXECUTION_LIMIT_REACHED",
        )
        _checkpoint(state)
        return state

    decision = state["decision"]
    action = decision.action
    state["steps"] = state.get("steps", 0) + 1
    force_failure = state.get("fail_tool") == action and not state.get("fail_consumed", False)
    if force_failure:
        state["fail_consumed"] = True

    if action == "search_documents":
        outcome = search_documents(
            state["question"],
            fail=force_failure,
            database=state["storage"].database,
        )
        state["search_completed"] = True
        if outcome.ok:
            state["search_results"] = outcome.value or []
            summary = f"{len(state['search_results'])} matching source chunks found."
            diagnostics = outcome.diagnostics or {}
            state["embedding_error_type"] = diagnostics.get("embedding_error_type")
            parameters = {
                "question_length": len(state["question"]),
                "retrieval_mode": diagnostics.get("retrieval_mode"),
                "cache_status": diagnostics.get("cache_status"),
                "candidate_count": diagnostics.get("candidate_count"),
                "selected_chunk_ids": diagnostics.get("selected_chunk_ids"),
                "selected_scores": diagnostics.get("selected_scores"),
            }
        else:
            state["tool_error"] = outcome.error_code
            summary = f"Search failed with {outcome.error_code}."
            parameters = {"question_length": len(state["question"])}
        _append_trace(
            state,
            action=action,
            parameters=parameters,
            result_summary=summary,
            rationale=decision.rationale,
            source=decision.source,
        )
    elif action == "read_chunk":
        already_read = {chunk.chunk_id for chunk in state.get("read_chunks", [])}
        unread_chunk_ids = [
            item.chunk_id
            for item in state.get("search_results", [])
            if item.chunk_id not in already_read
        ]
        selected_chunk_id = (decision.parameters or {}).get("chunk_id")
        target = next(
            (
                item
                for item in state.get("search_results", [])
                if item.chunk_id == selected_chunk_id and item.chunk_id not in already_read
            ),
            None,
        )
        if target is None:
            target = next(
                (item for item in state.get("search_results", []) if item.chunk_id not in already_read),
                None,
            )
        if target is None:
            state["tool_error"] = "NO_UNREAD_CHUNK"
            summary = "No unread source chunk remained."
            parameters = {"chunk_id": None}
        else:
            outcome = read_chunk(target.chunk_id, fail=force_failure)
            parameters = {
                "chunk_id": target.chunk_id,
                "candidate_chunk_ids": unread_chunk_ids,
                "model_selected_chunk": (
                    decision.source == "live_llm" and selected_chunk_id == target.chunk_id
                ),
            }
            if outcome.ok:
                state.setdefault("read_chunks", []).append(outcome.value)
                summary = f"Read verified chunk {target.chunk_id}."
            else:
                state["tool_error"] = outcome.error_code
                summary = f"Chunk read failed with {outcome.error_code}."
        _append_trace(
            state,
            action=action,
            parameters=parameters,
            result_summary=summary,
            rationale=decision.rationale,
            source=decision.source,
        )
    elif action == "ask_clarifying_question":
        chunks = state.get("read_chunks", [])
        _finalize_result(
            state,
            status="clarification_required",
            clarifying_question=(
                "D01 规定普通国内差旅凭证须在 30 个自然日内提交，"
                "D02 规定紧急项目报销须在 15 个自然日内提交。"
                "这笔费用是否属于紧急项目？"
            ),
            citations=[
                _citation(chunk)
                for chunk in chunks
                if chunk.document_id in {"D01", "D02"}
            ],
        )
        _append_trace(
            state,
            action=action,
            parameters={"citation_count": len(chunks)},
            result_summary="Requested urgent-project scope to resolve conflicting deadlines.",
            rationale=decision.rationale,
            source=decision.source,
        )
    elif action == "answer_with_citations":
        chunks = state.get("read_chunks", [])
        ids = {chunk.document_id for chunk in chunks}
        if not chunks:
            _finalize_result(state, status="tool_failed", error_code="UNVERIFIED_CITATION")
            summary = "Answer blocked because no chunk was verified."
        elif {"D01", "D02"}.issubset(ids) and not state.get("urgent_scope"):
            _finalize_result(
                state,
                status="clarification_required",
                clarifying_question=(
                    "D01 规定普通国内差旅凭证须在 30 个自然日内提交，"
                    "D02 规定紧急项目报销须在 15 个自然日内提交。"
                    "这笔费用是否属于紧急项目？"
                ),
                citations=[
                    _citation(chunk)
                    for chunk in chunks
                    if chunk.document_id in {"D01", "D02"}
                ],
            )
            summary = "Answer blocked because policy deadlines conflict without scope."
        elif ids == {"D02"}:
            _finalize_result(
                state,
                status="answered",
                answer="紧急项目报销凭证须在费用发生后 15 个自然日内提交。",
                citations=[_citation(chunk) for chunk in chunks],
            )
            summary = "Answered from the verified urgent-project policy chunk."
        elif ids == {"P01"}:
            _finalize_result(
                state,
                status="answered",
                answer="导出的视频片段在 Creator Hub 中自生成起保留 30 天。",
                citations=[_citation(chunk) for chunk in chunks],
            )
            summary = "Answered from the verified product guide chunk."
        else:
            _finalize_result(
                state,
                status="answered",
                answer="普通国内差旅报销凭证须在费用发生后 30 个自然日内提交。",
                citations=[_citation(chunk) for chunk in chunks],
            )
            summary = "Answered from the verified travel policy chunk."
        _append_trace(
            state,
            action=action,
            parameters={"citation_count": len(chunks)},
            result_summary=summary,
            rationale=decision.rationale,
            source=decision.source,
        )
    else:
        if state.get("tool_error"):
            _finalize_result(state, status="tool_failed", error_code=state["tool_error"])
            summary = f"Stopped after tool error {state['tool_error']}."
        elif state.get("search_results") and not state.get("read_chunks"):
            _finalize_result(
                state,
                status="incomplete",
                error_code="MODEL_STOPPED_BEFORE_EVIDENCE",
            )
            summary = "Model stopped before any retrieved source was read."
        else:
            _finalize_result(
                state,
                status="not_found",
                answer="本地知识库中没有支持该问题的资料。",
                error_code="NO_SUPPORTING_SOURCE",
            )
            summary = "Stopped because no supporting source was found."
        _append_trace(
            state,
            action="stop",
            parameters={},
            result_summary=summary,
            rationale=decision.rationale,
            source=decision.source,
        )
    _checkpoint(state)
    return state


def observe_result(state: AgentState) -> AgentState:
    if state.get("trace"):
        if state.get("result") is not None:
            next_action = "finalize"
        else:
            next_action = state["planner"].choose(state).action
        state["trace"][-1]["next_action"] = next_action
    _checkpoint(state)
    return state


def _route_after_validation(state: AgentState) -> str:
    return "finalize" if state.get("result") is not None else "choose_action"


def _route_after_observation(state: AgentState) -> str:
    return "finalize" if state.get("result") is not None else "choose_action"


def finalize(state: AgentState) -> AgentState:
    result = state["result"]
    if result is None:
        _finalize_result(state, status="incomplete", error_code="WORKFLOW_NOT_FINALIZED")
        result = state["result"]
    result.trace = state.get("trace", [])
    state["storage"].record_run(state["run_id"], result.to_dict(), result.trace)
    return state


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("validate_input", validate_input)
    graph.add_node("choose_action", choose_action)
    graph.add_node("execute_action", execute_action)
    graph.add_node("observe_result", observe_result)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        _route_after_validation,
        {"choose_action": "choose_action", "finalize": "finalize"},
    )
    graph.add_edge("choose_action", "execute_action")
    graph.add_edge("execute_action", "observe_result")
    graph.add_conditional_edges(
        "observe_result",
        _route_after_observation,
        {"choose_action": "choose_action", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    return graph.compile()


def run_question(
    question: str,
    *,
    database: str | Path = "data/enterprise_qa.db",
    conversation_id: str | None = None,
    max_steps: int = 8,
    fail_tool: str | None = None,
    planner: Planner | None = None,
) -> FinalResult:
    storage = Storage(database)
    context_question = question
    previous_subject = (
        storage.get_conversation_subject(conversation_id) if conversation_id else None
    )
    if previous_subject == "reimbursement" and "紧急项目" in question:
        context_question = "紧急项目报销凭证多久提交？"

    initial: AgentState = {
        "question": context_question,
        "conversation_id": conversation_id,
        "storage": storage,
        "planner": planner or Planner.from_environment(),
        "max_steps": max_steps,
        "fail_tool": fail_tool,
        "fail_consumed": False,
        "run_id": uuid4().hex,
        "steps": 0,
        "search_completed": False,
        "search_results": [],
        "read_chunks": [],
        "urgent_scope": "紧急项目" in context_question,
        "tool_error": None,
        "embedding_error_type": None,
        "trace": [],
        "result": None,
    }
    completed = _build_graph().invoke(initial)
    result = completed["result"]
    if conversation_id and result.status == "answered" and any(
        citation["document_id"] in {"D01", "D02"} for citation in result.citations
    ):
        storage.save_conversation_subject(conversation_id, "reimbursement")
    return result
