# Live LLM Evidence

Status: verified on 2026-10-29.

A real OpenAI-compatible gateway call selected constrained, validated actions for the policy-conflict request. The actual safe output records `decision_source: "live_llm"`; the trace shows the online action-selection source at every step.

- Input: [`04-live-llm-input.json`](04-live-llm-input.json)
- Safe final output: [`04-live-llm-output.json`](04-live-llm-output.json)
- Safe execution trace: [`04-live-llm-trace.json`](04-live-llm-trace.json)

The live call proves only the bounded action-selection path. The embedding retriever remained in its separately configured `hash_fallback` mode for this run. No credential, gateway URL, prompt body, header, raw embedding vector, or raw provider response is recorded.
