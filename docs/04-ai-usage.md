# 04 AI Usage

AI assistance helped draft the embedding-retrieval design, Clause-Bridge algorithm, Python implementation, tests, safe synthetic evidence, and documentation. The implementation was manually checked by running the complete test suite and representative CLI paths.

Claims supported by executable evidence are limited to local Clause-Bridge chunking, vector cache invalidation, deterministic hash-vector retrieval, source-read citation enforcement, conflict clarification, tool-error handling, and the recorded examples. A real constrained action-selection gateway request is evidenced by the safe `live_llm` record in `examples/04-live-llm-*`; it does not claim live embedding quality. No API key, token, password, private URL, raw vector, prompt payload, or raw provider response was included in source, documentation, tests, or examples.
