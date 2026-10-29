# Xiaoying Q3 Enterprise Knowledge QA Agent

A self-contained Python CLI for the third Xiaoying assessment question: enterprise knowledge Q&A with Clause-Bridge chunking, embedding retrieval, source verification, conflict clarification, safe fallback, bounded actions, and auditable traces.

## Review Entry Point

1. Read `docs/01-requirements.md`, `docs/02-solution.md`, and `docs/03-evaluation.md`.
2. Run the complete suite from this directory: `python -m pytest -v`.
3. Inspect actual request/output/trace evidence in `examples/`.
4. Start with the conflict path:

```powershell
python main.py ask --question "报销凭证多久提交？" --database data/review.db
```

It returns `clarification_required` with the 30-day D01 and 15-day D02 citations because the request does not state whether the expense belongs to an urgent project.

## Installation and Run

Run commands from `xiaoying-q3-enterprise-knowledge-qa-agent/` using the selected Conda/PyCharm interpreter:

```powershell
python -m pip install -r requirements.txt
python main.py ask --question "普通国内差旅报销凭证多久提交？"
python -m pytest -v
```

The direct entry point is only `python main.py`. The project uses the repository-required root package `enterprise_qa/`, not a `src/` layout.

## Retrieval Design

The local synthetic policy corpus is split by **Clause-Bridge Chunking**. It starts at clause/sentence boundaries, then keeps a deadline or policy rule together with its nearby scope and qualification sentence. That is why the D02 chunk keeps both “紧急项目” and “15 个自然日” in a single citation-ready source.

Chunks are embedded before retrieval. With `EMBEDDING_*` configured, the agent calls a compatible embedding endpoint and runs cosine similarity locally. Without configuration or after a safe embedding failure, it uses a deterministic local feature-hash vector fallback; this is still vector search, but it is not claimed as proof of a live embedding model. Retrieval keeps the strongest chunk per document before filling Top-K, which helps generic policy questions surface conflicting sources instead of one document monopolizing results.

The ignored SQLite runtime database caches vectors using the chunk corpus fingerprint and embedding model/mode fingerprint. A changed corpus, Clause-Bridge version, provider mode, or model creates a new cache entry.

## Configuration

Copy `.env.example` to `.env` only for local configuration. Shell/PyCharm variables take precedence.

```dotenv
# Do not commit real credentials. These values configure an OpenAI-compatible gateway.
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
# responses is preferred; use chat_completions if the gateway lacks /v1/responses.
LLM_API_MODE=chat_completions

# Optional embedding model; separate from LLM_* above
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=
```

`LLM_API_MODE=responses` uses the Responses API. Set it to `chat_completions` for a compatible gateway that lacks `/v1/responses`. The final JSON is written to stdout. stderr carries only concise missing-action-model or embedding/action exception-type fallback notices. Traces carry safe retrieval mode, cache status, candidate count, selected IDs, and rounded scores; they never contain vectors, credentials, prompts, raw responses, or private URLs.

## Known Limitations and No-Secret Policy

- The corpus is synthetic; it is not a production enterprise document system.
- No full embedding configuration was available during the recorded verification, so no live-embedding quality claim is made.
- The offline hash-vector path validates chunking, vector indexing, and conflict behavior but does not prove production semantic-retrieval quality.
- Never commit `.env`, API keys, tokens, passwords, private URLs, generated SQLite databases, virtual environments, caches, or IDE metadata.
