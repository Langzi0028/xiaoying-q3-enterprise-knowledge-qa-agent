# 02 Solution

## Workflow

```text
validate_input
-> choose_action
-> execute_action
-> observe_result
-> choose_action | finalize
```

The application builds this loop with LangGraph `StateGraph`. `choose_action` selects one allowed action, `execute_action` invokes the matching local tool, and `observe_result` computes the next allowed action using the new state. This makes the action change visible in the trace, for example search -> read_chunk -> clarification on a policy conflict.

## Components

- `main.py` imports and calls the small CLI only.
- `enterprise_qa/knowledge_base.py` holds non-secret, versioned fixtures and deterministic query ranking.
- `enterprise_qa/tools.py` returns structured success or safe failure results for search and chunk reading.
- `enterprise_qa/planner.py` supplies the constrained action-selection boundary.
- `enterprise_qa/workflow.py` applies execution limits, citation verification, and final response guards.
- `enterprise_qa/storage.py` stores safe run output, traces, short conversation subject, and graph checkpoints in SQLite.

## Dynamic decisions

The only valid actions are `search_documents`, `read_chunk`, `ask_clarifying_question`, `answer_with_citations`, and `stop`. The fallback planner searches first, reads every retrieved chunk, asks a clarification if D01 and D02 conflict without scope, and answers only from read chunks. Tool errors route to `stop`; no search results also route to `stop` with a different final status. The trace shows both observed result summaries and the selected subsequent action.

## Live-model boundary

When `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` are all configured, the planner attempts one small online action-selection request. Its prompt carries only action names, counts, question length, and safe state flags. The model must emit a JSON object whose action exactly matches the deterministic legal action for the current state. The application validates it before execution. A successful validated request is labelled `live_llm`; network exceptions and invalid output use labelled deterministic fallbacks. No gateway URL, credential, header, complete prompt, raw response, or chain-of-thought is stored.

## Limits and safety

The default tool/action limit is eight. Exhaustion returns `incomplete` with `EXECUTION_LIMIT_REACHED`. An ordinary answer requires a chunk read during that run and copies citation metadata from it. A D01/D02 conflict must cite both chunks and must return a clarification question. JSON results are printed on stdout; only concise missing-configuration or exception-type notices are printed to stderr.

## Version/layout boundary

The dependency manifest requests LangGraph and `langchain-openai` 1.x, plus `python-dotenv` and pytest. The repository convention requires a root package, so this project intentionally uses `enterprise_qa/` rather than an external `src/` example layout.
