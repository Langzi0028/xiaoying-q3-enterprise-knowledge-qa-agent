# 03 Evaluation

## Commands and actual result

After the compatible gateway correction, `python -m pytest -v` was run from the question root on 2026-10-29. The suite reported **34 passed**. It covers Clause-Bridge boundary preservation, stable chunks, hash-vector fallback determinism, a direct string-array request to compatible embedding gateways, invalid live embedding response fallback, cosine ranking, source-diversity selection, cache invalidation for embedding and corpus changes, source-read citations, policy conflict clarification (including extra candidates), low-similarity rejection, tool failures, empty input, invalid action-model output, SQLite audit, CLI stdout/stderr separation, and execution limits.

## Evidence links

- Clear ordinary-travel answer: [`examples/01-clear-policy-input.json`](../examples/01-clear-policy-input.json), [`output`](../examples/01-clear-policy-output.json), [`trace`](../examples/01-clear-policy-trace.json). A real gateway run shows `live_llm` plus `live_embedding`, then a verified D01 source read and cited answer.
- Policy conflict: [`examples/02-conflict-clarification-input.json`](../examples/02-conflict-clarification-input.json), [`output`](../examples/02-conflict-clarification-output.json), [`trace`](../examples/02-conflict-clarification-trace.json). A real gateway run retrieves D01/D02 with live embeddings, reads both source chunks, and asks for urgent-project scope instead of choosing a deadline.
- Unsupported question: [`examples/03-not-found-input.json`](../examples/03-not-found-input.json), [`output`](../examples/03-not-found-output.json), [`trace`](../examples/03-not-found-trace.json). A real gateway run rejects low-similarity live-embedding candidates and returns explicit `not_found`.
- Live action-model evidence: [`examples/04-live-llm-evidence.md`](../examples/04-live-llm-evidence.md), [`input`](../examples/04-live-llm-input.json), [`output`](../examples/04-live-llm-output.json), and [`trace`](../examples/04-live-llm-trace.json). The constrained gateway decision recorded `decision_source: "live_llm"`; the numbered evidence sets additionally prove real `live_embedding` retrieval without retaining raw vectors.

## Failure behavior

- Whitespace input returns `invalid_request` before an action.
- Forced search/read failure returns `tool_failed` and preserves the safe error in Trace.
- Invalid action-model data is rejected and uses safe fallback action sequencing.
- Invalid live embedding response and embedding request exceptions use local hash vectors without logging response bodies. The real compatible-gateway path sends an `input` array of source strings directly, avoiding the gateway-incompatible token-array transformation.
- Step exhaustion returns `incomplete` with `EXECUTION_LIMIT_REACHED`.

## Known limitations

The compatible gateway has been exercised with live LLM and live embedding calls against only synthetic local policy text. The corpus remains small and synthetic, so this does not establish production retrieval quality, calibrated threshold quality, or enterprise document permission behavior.
