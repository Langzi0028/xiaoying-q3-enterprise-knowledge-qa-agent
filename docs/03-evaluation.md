# 03 Evaluation

## Commands and actual result

After the embedding upgrade, `python -m pytest -v` was run from the question root on 2026-10-29. The suite reported **30 passed**. It covers Clause-Bridge boundary preservation, stable chunks, hash-vector fallback determinism, invalid live embedding response fallback, cosine ranking, source-diversity selection, cache invalidation for embedding and corpus changes, source-read citations, policy conflict clarification, tool failures, empty input, invalid action-model output, SQLite audit, CLI stdout/stderr separation, and execution limits.

## Evidence links

- Clear ordinary-travel answer: [`examples/01-clear-policy-input.json`](../examples/01-clear-policy-input.json), [`output`](../examples/01-clear-policy-output.json), [`trace`](../examples/01-clear-policy-trace.json). It shows embedding retrieval followed by a verified D01 source read and cited answer.
- Policy conflict: [`examples/02-conflict-clarification-input.json`](../examples/02-conflict-clarification-input.json), [`output`](../examples/02-conflict-clarification-output.json), [`trace`](../examples/02-conflict-clarification-trace.json). It shows vector retrieval of D01/D02, reads both source chunks, and asks for urgent-project scope instead of choosing a deadline.
- Unsupported question: [`examples/03-not-found-input.json`](../examples/03-not-found-input.json), [`output`](../examples/03-not-found-output.json), [`trace`](../examples/03-not-found-trace.json). It shows no supported positive-similarity source and an explicit `not_found` result.
- Live model/embedding status: [`examples/04-live-llm-evidence.md`](../examples/04-live-llm-evidence.md). No complete compatible configuration was available during verification, so neither live action-model nor live embedding quality is claimed.

## Failure behavior

- Whitespace input returns `invalid_request` before an action.
- Forced search/read failure returns `tool_failed` and preserves the safe error in Trace.
- Invalid action-model data is rejected and uses safe fallback action sequencing.
- Invalid live embedding response and embedding request exceptions use local hash vectors without logging response bodies.
- Step exhaustion returns `incomplete` with `EXECUTION_LIMIT_REACHED`.

## Known limitations

The project has not executed an external embedding request because all three embedding variables were unavailable. The `hash_fallback` path is a deterministic local vector index used for offline boundary testing; it is not a quality claim for production semantic embeddings. Fixtures are synthetic and no external enterprise document permissions are implemented.
