# Live LLM Evidence

Status: verified on 2026-10-29.

A real OpenAI-compatible gateway call selected constrained, validated actions for the policy-conflict request. The actual safe output records `decision_source: "live_llm"`; the trace shows the online action-selection source at every step.

- Input: [`04-live-llm-input.json`](04-live-llm-input.json)
- Safe final output: [`04-live-llm-output.json`](04-live-llm-output.json)
- Safe execution trace: [`04-live-llm-trace.json`](04-live-llm-trace.json)

The first live action-selection evidence above proves the bounded Agent decision path. The three numbered evidence sets (`01` through `03`) were subsequently rerun with both `decision_source: "live_llm"` and `retrieval_mode: "live_embedding"`; their traces record only safe scores, IDs, modes, and cache state. No credential, gateway URL, prompt body, header, raw embedding vector, or raw provider response is recorded.
