# 02 Solution

## Workflow

```text
validate_input
-> choose_action
-> execute_action
-> observe_result
-> choose_action | finalize
```

The application builds this loop with LangGraph `StateGraph`. `choose_action` selects one allowed action, `execute_action` invokes the matching local tool, and `observe_result` computes the next action using tool output. For example, a generic reimbursement query follows search -> source reads -> clarification when it observes D01 and D02.

## Clause-Bridge indexing

`enterprise_qa/corpus.py` keeps raw safe source documents; the production retrieval path does not use fixed hand-authored chunks. `enterprise_qa/chunking.py` applies Clause-Bridge Chunking: it first uses labelled clause and sentence boundaries, detects policy anchors such as scope, deadline, exception, or confirmation requirements, and emits a compact chunk joining the anchor with neighboring scope/qualification text. This prevents a policy condition from being separated from its numeric rule. Stable chunk IDs and a corpus fingerprint include the splitter version.

## Vector retrieval

`enterprise_qa/embeddings.py` returns OpenAI-compatible embeddings only when all `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, and `EMBEDDING_MODEL` values exist. Otherwise it returns deterministic local feature-hash vectors from Chinese character n-grams, token features, and compact policy-concept features. `enterprise_qa/vector_index.py` runs cosine similarity locally and chooses a highest-scoring chunk per document before filling the requested Top-K. It stores vectors only in ignored SQLite tables keyed by chunk-corpus and embedding fingerprints, so changed source text, chunk algorithm, mode, or model rebuilds the cache.

## Components and safety

- `knowledge_base.py`: retrieval facade and exact generated chunk lookup.
- `tools.py`: safe search/read tool outcomes and non-sensitive retrieval diagnostics.
- `workflow.py`: execution cap, source-read gate, citation guard, conflict clarification, and trace creation.
- `storage.py`: safe run records/checkpoints; the same question-local database also contains generated vector cache tables.
- `planner.py`: separate optional action-selection model boundary using `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and `LLM_API_MODE`.

The only valid Agent actions are `search_documents`, `read_chunk`, `ask_clarifying_question`, `answer_with_citations`, and `stop`. A normal answer requires chunks read during the current run. The D01/D02 conflict must cite both chunks and request scope. The default action limit is eight; exhaustion returns `incomplete` with `EXECUTION_LIMIT_REACHED`.

## Safe fallback and output boundary

The embedding provider and action-selection model are independently configured. `LLM_API_MODE=responses` uses the Responses API; set it to `chat_completions` for a compatible gateway without `/v1/responses`. A missing embedding configuration silently selects `hash_fallback` and records that safe mode in trace data. A live embedding request failure prints only `Embedding request failed: <ExceptionType>; using local vector fallback.` to stderr. Trace data includes retrieval mode, cache status, candidate count, selected chunk IDs, and rounded scores; no raw vector, secret, gateway URL, prompt, request, raw response, or chain-of-thought is recorded. The final machine-readable JSON remains stdout-only.
