# 05 Retrospective

## Hardest issue

The main design challenge was making vector retrieval useful for policy clauses without cutting a deadline away from the condition that governs it. Clause-Bridge Chunking keeps scope, requirement, and nearby qualification together, while diversity-aware retrieval allows conflicting documents to surface in the same Agent run.

## Learning outcomes

- A vector index still needs document-aware selection for policy conflicts; simple Top-K can overrepresent one source.
- Citation quality depends on chunk boundaries, not merely embedding scores.
- An offline deterministic vector fallback makes the retrieval pipeline testable without misrepresenting it as a live semantic model evaluation.

## Actual effort and status

The embedding upgrade includes a raw local corpus, generated chunks, configurable embedding endpoint, deterministic fallback, cosine index, SQLite fingerprint cache, 30 regression tests, and regenerated evidence. The previous keyword-branch retriever has been replaced by the vector index.

## Risks and next steps

The constrained live action-selection request is verified, but live embedding evidence remains unavailable until a compatible `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, and `EMBEDDING_MODEL` are supplied. The next step is a sanctioned online embedding run to inspect a real `live_embedding` retrieval trace against a larger approved document corpus. Production deployment would additionally need document access control, ingestion validation, and evaluation data.
