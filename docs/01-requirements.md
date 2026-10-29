# 01 Requirements

## User and goal

Employees need trustworthy answers to enterprise policy and product questions. The agent indexes safe local enterprise documents, retrieves the most relevant chunks with embeddings, reads the cited source chunks, and returns an answer only when the evidence supports it.

## Scope

- A local Python CLI invoked with `python main.py ask --question "..."`.
- A safe synthetic knowledge corpus with versioned raw documents, Clause-Bridge chunks, document IDs, dates, and exact source text.
- Configurable OpenAI-compatible embeddings with local vector cosine search and deterministic hash-vector fallback.
- Search/read tools, bounded LangGraph orchestration, optional action-selection LLM, SQLite audit/checkpoints/vector cache.
- Cited answers, conflict clarification, no-source responses, tool errors, and safe conversation follow-ups.

## Non-goals

No HTTP API, UI, authorization, external enterprise content, production database, or uploaded documents is included.

## Success criteria

- Clause-Bridge chunks preserve a policy requirement together with its applicability condition.
- Vector search surfaces D01 and D02 for a generic reimbursement deadline question, but prioritizes D01 for ordinary travel and D02 for urgent-project requests.
- Answers cite only chunks read in the current run.
- The D01 30-day versus D02 15-day conflict returns a clarification request when urgent-project scope is missing.
- Missing/failed model configuration uses a labelled fallback without exposing configuration values, vectors, prompts, or private URLs.
- Corpus or embedding-model changes invalidate the SQLite vector cache.

## Constraints

The fixtures and fallback vectors are deterministic for evaluation. They do not demonstrate external embedding quality unless a configured online request succeeds.
