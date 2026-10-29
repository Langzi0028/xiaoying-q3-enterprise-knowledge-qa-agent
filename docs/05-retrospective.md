# 05 Retrospective

## Hardest issue

The key problem was separating a useful agent loop from an unsafe free-form answer generator. The implementation therefore keeps action selection small and validates every action and citation against observable program state.

## Learning outcomes

- A source-backed Q&A agent needs a chunk-read gate, not just retrieval snippets.
- Conflict handling should preserve ambiguity and ask for the missing scope.
- A trace can explain state transitions without recording private prompts or model chain-of-thought.

## Actual effort and status

Core implementation, tests, example generation, and documentation were completed in this session. Live-model evidence remains unfinished because the necessary three environment variables were unavailable; this limitation is recorded rather than simulated.

## Risks and next steps

The live action adapter is intentionally strict: it accepts only the exact safe action that the deterministic validator expects. A next step with an authorized test gateway is to execute one real call, inspect the safe `live_llm` trace flag, and add an actual sanitized evidence record. A production successor would require authenticated document retrieval and a reviewed permission model.
