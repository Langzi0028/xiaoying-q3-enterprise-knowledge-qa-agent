# 03 Evaluation

## Commands and actual result

From the question root, `python -m pytest -v` was run on 2026-10-29. The suite reported **20 passed**. It covers clear answers, conflict clarification, limit exhaustion, missing source material, paraphrase retrieval, safe conversation follow-up, invalid input, search/read failures, invalid live-model output, redacted SQLite persistence, and CLI stdout/stderr separation.

## Evidence links

- Clear policy answer: [`examples/01-clear-policy-input.json`](../examples/01-clear-policy-input.json), [`output`](../examples/01-clear-policy-output.json), [`trace`](../examples/01-clear-policy-trace.json). It demonstrates search -> read_chunk -> answer with D01 citation.
- Policy conflict: [`examples/02-conflict-clarification-input.json`](../examples/02-conflict-clarification-input.json), [`output`](../examples/02-conflict-clarification-output.json), [`trace`](../examples/02-conflict-clarification-trace.json). It demonstrates search -> two source reads -> clarification with D01/D02 citations rather than a guessed deadline.
- Unsupported question: [`examples/03-not-found-input.json`](../examples/03-not-found-input.json), [`output`](../examples/03-not-found-output.json), [`trace`](../examples/03-not-found-trace.json). It demonstrates the no-search-result branch and explicit `not_found` result.
- Live-model status: [`examples/04-live-llm-evidence.md`](../examples/04-live-llm-evidence.md). No real model configuration was available during this verification, so no live-model quality claim is made.

## Failure behavior

- Whitespace input returns `invalid_request` before any tool action.
- Forced search/read tool failure returns `tool_failed` and preserves the failure in the trace.
- Invalid model action data is rejected and falls back to verified action sequencing.
- Limit exhaustion returns `incomplete` with `EXECUTION_LIMIT_REACHED`.

## Known limitations

No real-model request could be executed because the required configuration was unavailable. The SQLite checkpoint table is an application audit checkpoint and not a LangGraph-built-in checkpointer; the workflow itself is a real LangGraph `StateGraph`. Fixtures are synthetic and no external enterprise document permissions are implemented. The shared Conda environment emitted unrelated dependency-resolver conflict notices for preinstalled `langchain`/`langchain-qwq`; this question-local requirement set installed successfully and the Q3 suite passed afterward.
