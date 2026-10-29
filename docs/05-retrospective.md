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

Real action-selection and embedding requests are verified against the configured compatible gateway. A gateway-specific issue required bypassing a wrapper that transformed the embedding input into token arrays; the direct compatible request now sends a string array and is protected by regression tests. The next step is evaluation against a larger approved document corpus to calibrate similarity thresholds. Production deployment would additionally need document access control, ingestion validation, and evaluation data.
