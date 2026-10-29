# Enterprise Knowledge QA Agent: Embedding Retrieval Design

## Change Goal

Replace the question-local keyword/synonym retriever with embedding-based retrieval over chunks generated from the existing synthetic enterprise knowledge corpus. Preserve the public CLI result structure, source-verification rule, conflict-clarification behavior, bounded Agent loop, and safe offline execution.

## Contract Change

This is a question-local retrieval and configuration contract change.

- New optional environment variables in `.env.example`:
  - `EMBEDDING_API_KEY`
  - `EMBEDDING_BASE_URL`
  - `EMBEDDING_MODEL`
- Existing `OPENAI_*` variables remain solely for the constrained action-selection model; embedding configuration is independent.
- `search_documents` changes internally from keyword matching to vector similarity search. Its safe returned metadata gains a rounded `retrieval_score` and `retrieval_mode`; the final CLI JSON, citation fields, and action names do not change.
- SQLite gains generated embedding-cache tables. Database files stay ignored and no raw vector is printed, stored in examples, or included in Trace output.

## Corpus And Chunking

The embedded corpus is generated locally from the project-owned synthetic policy/product documents; it does not download, upload, or use real enterprise content.

The splitter uses **Clause-Bridge Chunking**, designed for policy questions where a numeric requirement and its applicability condition must remain together:

1. Start at document title, numbered/labelled clauses, and sentence boundaries rather than fixed character windows.
2. Detect an obligation anchor: a sentence containing a deadline, amount, prohibition, exception, eligibility condition, or imperative policy term.
3. Construct the primary chunk from the closest preceding scope sentence through the next exception/qualification sentence. The title, document ID, version, and effective date are added as embedding context.
4. Emit a small overlapping bridge chunk around each boundary anchor so a condition such as "urgent project" and its "15 calendar days" deadline remain retrievable together even if a longer source section grows later.
5. Deduplicate identical normalized chunks and retain a stable chunk ID derived from document ID, version, and ordinal position.

This produces compact, citation-ready clauses instead of generic fixed windows. It deliberately favors legal/policy meaning preservation over uniform chunk size.

## Embedding And Retrieval

When all `EMBEDDING_*` values are configured, the agent sends each local chunk/query to the configured OpenAI-compatible embedding endpoint and performs cosine-similarity search locally. Only the configured provider receives the local synthetic text; no API key, gateway URL, vector, request body, or raw response is persisted or printed.

When configuration is absent or an embedding request fails, the agent uses a deterministic local feature-hash vector fallback. The fallback remains a real vector index/search operation but is explicitly labelled `hash_fallback`, not presented as a live embedding-model evaluation.

Retrieval uses two stages:

1. Retrieve the top candidate chunks by cosine similarity.
2. Apply diversity-aware source selection: retain the strongest relevant chunk per document before filling remaining slots by score. This ensures a generic reimbursement-deadline question can surface both D01 and D02 rather than allowing one longer document to monopolize the result set.

`read_chunk` still retrieves exact source text by ID. The answer/clarification nodes remain forbidden from citing a search excerpt alone.

## Index Cache And Invalidation

SQLite stores a generated vector index keyed by:

- corpus fingerprint: source document IDs, versions, dates, text, and Clause-Bridge algorithm version;
- embedding fingerprint: retrieval mode and configured model name; and
- stable chunk ID.

If any fingerprint changes, the agent rebuilds the cache before searching. The cache stores the vector only in the ignored runtime database. The trace records only cache state (`hit` or `rebuilt`), retrieval mode, candidate count, selected chunk IDs, and rounded scores.

## Error And Safety Behavior

- Missing `EMBEDDING_*` configuration: continue with `hash_fallback`; print no additional warning because `decision_source` and trace identify the mode.
- Live embedding exception: print a concise `Embedding request failed: <ExceptionType>; using local vector fallback.` notice on stderr; continue with local vectors.
- Invalid/mismatched embedding dimensions: discard the cache, fall back safely for that run, and never compare incompatible vectors.
- Search-tool injection failure continues to produce the existing `SEARCH_UNAVAILABLE` result.
- The execution cap, conflict clarification, and no-source behavior remain unchanged.

## Acceptance Criteria

- The in-memory documents are transformed into deterministic Clause-Bridge chunks before retrieval.
- Search uses cosine similarity over vectors, not keyword branches, in both live-embedding and local-fallback modes.
- Generic reimbursement queries retrieve D01 and D02; ordinary domestic-travel and urgent-project queries prioritize their respective source document.
- Search traces expose safe retrieval diagnostics but never raw vectors or configuration details.
- Corpus or embedding-model/configuration changes invalidate and rebuild the cached index.
- Tests cover chunk boundary preservation, vector ranking, fallback mode, live-embedding failure fallback, cache invalidation, conflict clarification, and existing failure paths.
- Documentation and actual examples distinguish configured embedding retrieval from offline fallback; no live claim is made without a real configured request.
