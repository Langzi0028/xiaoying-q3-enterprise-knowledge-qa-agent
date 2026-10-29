# Embedding Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Question 3's keyword retriever with embedding-based Clause-Bridge chunk retrieval while preserving source verification and conflict clarification.

**Architecture:** Raw synthetic documents are split with Clause-Bridge Chunking, embedded with an optional OpenAI-compatible provider or a deterministic local feature-hash fallback, and searched by cosine similarity. SQLite caches generated vectors using corpus and embedding fingerprints; the existing LangGraph workflow receives safe retrieval diagnostics only.

**Tech Stack:** Python 3.12, LangGraph, `langchain-openai`, SQLite, `python-dotenv`, standard-library hashing/math, pytest.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `enterprise_qa/corpus.py` | Local raw synthetic source documents. |
| `enterprise_qa/chunking.py` | Clause-Bridge splitting and corpus fingerprinting. |
| `enterprise_qa/embeddings.py` | Live compatible embedding client and deterministic hash-vector fallback. |
| `enterprise_qa/vector_index.py` | Cosine ranking, source diversity selection, cache use/invalidation. |
| `enterprise_qa/knowledge_base.py` | Public search/read facade over generated chunks. |
| `enterprise_qa/storage.py` | Embedding-cache tables in the question-local runtime SQLite database. |
| `enterprise_qa/tools.py` | Safe search outcome carrying result diagnostics. |
| `enterprise_qa/workflow.py` | Trace only safe retrieval mode, cache status, selected IDs/counts/rounded scores. |

### Task 1: Specify the new retrieval behavior with failing tests

**Files:**
- Create: `tests/test_chunking.py`
- Create: `tests/test_embeddings.py`
- Create: `tests/test_vector_index.py`
- Modify: `tests/test_knowledge_base.py`
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Write failing Clause-Bridge tests.**

```python
def test_urgent_policy_chunk_keeps_scope_and_deadline_together():
    chunks = build_chunks(DOCUMENTS)
    target = next(chunk for chunk in chunks if "15" in chunk.text)
    assert "紧急项目" in target.text
    assert "15" in target.text


def test_chunk_ids_are_stable_for_unchanged_corpus():
    assert chunk_ids(build_chunks(DOCUMENTS)) == chunk_ids(build_chunks(DOCUMENTS))
```

- [ ] **Step 2: Write failing vector and cache tests.**

```python
def test_generic_reimbursement_query_diversifies_to_both_policies(tmp_path):
    index = VectorIndex.with_hash_fallback(tmp_path / "index.db")
    results = index.search("报销凭证多久提交？", build_chunks(DOCUMENTS), top_k=3)
    assert {result.document_id for result in results} >= {"D01", "D02"}


def test_cache_rebuilds_when_embedding_fingerprint_changes(tmp_path):
    index = VectorIndex.with_hash_fallback(tmp_path / "index.db", model_name="v1")
    index.search("报销", build_chunks(DOCUMENTS))
    changed = VectorIndex.with_hash_fallback(tmp_path / "index.db", model_name="v2")
    assert changed.search("报销", build_chunks(DOCUMENTS)).cache_status == "cache_rebuilt"
```

Also test: urgent-project query ranks D02 first; missing configuration selects hash fallback; invalid live vector payload and live request exceptions fall back; workflow trace excludes raw vectors.

- [ ] **Step 3: Run to prove the red state.**

```powershell
Set-Location xiaoying-q3-enterprise-knowledge-qa-agent
python -m pytest tests/test_chunking.py tests/test_embeddings.py tests/test_vector_index.py -v
```

Expected: FAIL because Clause-Bridge, embedding provider, and vector index modules are absent.

- [ ] **Step 4: Commit the test contract.**

```powershell
git add -- tests/test_chunking.py tests/test_embeddings.py tests/test_vector_index.py tests/test_knowledge_base.py tests/test_workflow.py
git commit -m "test(q3): define embedding retrieval contract"
```

### Task 2: Build the raw corpus and Clause-Bridge chunks

**Files:**
- Create: `enterprise_qa/corpus.py`
- Create: `enterprise_qa/chunking.py`
- Modify: `enterprise_qa/models.py`
- Modify: `enterprise_qa/knowledge_base.py`
- Test: `tests/test_chunking.py`

- [ ] **Step 1: Move D01, D02, and P01 into raw multi-sentence source documents.**

Each source carries ID, title, version, date, and a body. The production retrieval path must not retain fixed hand-authored chunks.

- [ ] **Step 2: Implement Clause-Bridge Chunking.**

Split first at labelled clause/sentence boundaries. For each deadline/eligibility/exception anchor, construct a chunk from its preceding scope through the following qualification. Emit only one overlapping bridge at genuine semantic boundaries. Prefix embedding text with source title/version/date. Generate stable chunk IDs from document ID, version, ordinal, and `CLAUSE_BRIDGE_VERSION`.

- [ ] **Step 3: Add corpus fingerprinting and exact source lookup.**

Fingerprint safe corpus text and splitter version. `read_chunk` must return the exact generated chunk and preserve its citation metadata.

- [ ] **Step 4: Run green checks.**

```powershell
python -m pytest tests/test_chunking.py tests/test_knowledge_base.py -v
```

Expected: PASS with D02 scope and 15-day deadline in one citation-ready chunk.

- [ ] **Step 5: Commit.**

```powershell
git add -- enterprise_qa/corpus.py enterprise_qa/chunking.py enterprise_qa/models.py enterprise_qa/knowledge_base.py tests/test_chunking.py tests/test_knowledge_base.py
git commit -m "feat(q3): add clause-bridge document chunks"
```

### Task 3: Implement live embedding configuration and hash-vector fallback

**Files:**
- Create: `enterprise_qa/embeddings.py`
- Modify: `.env.example`
- Modify: `requirements.txt`
- Test: `tests/test_embeddings.py`

- [ ] **Step 1: Add failing configuration/fallback tests and run them.**

```python
def test_missing_embedding_config_uses_hash_fallback(monkeypatch):
    remove_embedding_environment(monkeypatch)
    assert EmbeddingProvider.from_environment().mode == "hash_fallback"


def test_invalid_live_embedding_response_falls_back_without_payload_leak():
    provider = EmbeddingProvider.with_test_response({"data": []})
    batch = provider.embed(["safe text"])
    assert batch.mode == "hash_fallback"
    assert batch.error_type == "ValueError"
```

Run: `python -m pytest tests/test_embeddings.py -v`; expected initial FAIL.

- [ ] **Step 2: Implement deterministic local feature-hash embeddings.**

Normalize text; derive Chinese character n-grams and whitespace-token features; map with a stable hash into a fixed dimension; L2-normalize. This must expose `mode="hash_fallback"` and be deterministic across runs.

- [ ] **Step 3: Implement the optional compatible embedding client.**

Use only `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, and `EMBEDDING_MODEL`, all required before a network call. Validate vector count, numeric entries, and a common dimension. On live error or malformed result use local vectors and provide only an exception class to the CLI boundary.

- [ ] **Step 4: Update the configuration template.**

```dotenv
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=
```

- [ ] **Step 5: Run green tests and commit.**

```powershell
python -m pytest tests/test_embeddings.py -v
git add -- enterprise_qa/embeddings.py .env.example requirements.txt tests/test_embeddings.py
git commit -m "feat(q3): add configurable embedding provider"
```

### Task 4: Replace keyword branches with cached cosine vector retrieval

**Files:**
- Create: `enterprise_qa/vector_index.py`
- Modify: `enterprise_qa/storage.py`
- Modify: `enterprise_qa/knowledge_base.py`
- Modify: `enterprise_qa/tools.py`
- Test: `tests/test_vector_index.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Add embedding cache tables.**

Create `embedding_index_metadata` and `embedding_vectors` keyed by corpus fingerprint, embedding fingerprint, and chunk ID. Cache only in the ignored runtime database.

- [ ] **Step 2: Implement cosine similarity and cache invalidation.**

Rebuild when corpus content, Clause-Bridge version, provider mode, or embedding model changes. Reject cached vectors that do not match current query vector dimensions.

- [ ] **Step 3: Implement source-diversity selection.**

Rank all chunks by cosine score, take the strongest relevant chunk per document first, then fill the remaining top-K positions by score. Attach only safe rounded score, mode, cache state, candidate count, and selected IDs to diagnostics.

- [ ] **Step 4: Replace `search_documents` internals.**

Preserve the existing function/action names and `fail=True` failure injection. Eliminate keyword routing from production search; all queries must enter the vector index.

- [ ] **Step 5: Verify and commit.**

```powershell
python -m pytest tests/test_vector_index.py tests/test_tools.py tests/test_knowledge_base.py -v
git add -- enterprise_qa/vector_index.py enterprise_qa/storage.py enterprise_qa/knowledge_base.py enterprise_qa/tools.py tests/test_vector_index.py tests/test_tools.py tests/test_knowledge_base.py
git commit -m "feat(q3): retrieve document chunks by embeddings"
```

### Task 5: Preserve Agent behavior while adding safe diagnostics

**Files:**
- Modify: `enterprise_qa/workflow.py`
- Modify: `enterprise_qa/cli.py`
- Modify: `tests/test_workflow.py`
- Modify: `tests/test_regressions.py`

- [ ] **Step 1: Add a failing trace test.**

```python
def test_search_trace_contains_safe_embedding_diagnostics(tmp_path):
    result = run_question("报销凭证多久提交？", database=tmp_path / "q3.db")
    search = next(item for item in result.trace if item["action"] == "search_documents")
    assert search["parameters"]["retrieval_mode"] == "hash_fallback"
    assert search["parameters"]["candidate_count"] >= 2
    assert "[" not in str(search["parameters"])
```

- [ ] **Step 2: Run the related tests to show red.**

```powershell
python -m pytest tests/test_workflow.py tests/test_regressions.py -v
```

- [ ] **Step 3: Carry only safe diagnostics through `ToolOutcome` and the trace.**

Record retrieval mode, cache status, count, selected chunk IDs, and rounded scores. Never record vectors, prompts, API values, base URL, full raw embedding response, or provider request body.

- [ ] **Step 4: Emit concise embedding failure notice.**

If a live embedding attempt falls back, write only `Embedding request failed: <ExceptionType>; using local vector fallback.` to stderr once. Existing action-model error behavior remains unchanged.

- [ ] **Step 5: Run full workflow/regression tests and commit.**

```powershell
python -m pytest tests/test_workflow.py tests/test_regressions.py -v
git add -- enterprise_qa/workflow.py enterprise_qa/cli.py tests/test_workflow.py tests/test_regressions.py
git commit -m "feat(q3): trace safe embedding retrieval"
```

### Task 6: Refresh actual evidence and required documents

**Files:**
- Modify: `README.md`, `.env.example`
- Modify: `docs/01-requirements.md` through `docs/05-retrospective.md`
- Modify: `examples/01-*.json`, `examples/02-*.json`, `examples/03-*.json`
- Modify: `examples/04-live-llm-evidence.md`

- [ ] **Step 1: Run actual deterministic evidence commands.**

```powershell
python main.py ask --question "普通国内差旅报销凭证多久提交？" --database data/evidence.db
python main.py ask --question "报销凭证多久提交？" --database data/evidence.db
python main.py ask --question "公司股票什么时候上市？" --database data/evidence.db
```

Save exact input, actual output, and actual trace. Delete `data/evidence.db` when capture finishes.

- [ ] **Step 2: Attempt live embedding evidence only with real full configuration.**

Record `live_embedding` only when a real online embedding request succeeds. Otherwise record the actual fallback/unavailable state without secrets, URL, vectors, or payloads.

- [ ] **Step 3: Update docs from observed facts.**

Explain Clause-Bridge splitting, vector similarity/diversity selection, independent embedding/action config, cache invalidation, fallback boundaries, actual test count, and live-evidence limitation.

- [ ] **Step 4: Commit docs/evidence.**

```powershell
git add -- README.md .env.example docs examples
git commit -m "docs(q3): document embedding retrieval"
```

### Task 7: Full verification and delivery commit

**Files:**
- Modify if needed: `docs/03-evaluation.md`, `docs/05-retrospective.md`

- [ ] **Step 1: Install and run all tests.**

```powershell
python -m pip install -r requirements.txt
python -m pytest -v
```

Expected: all tests pass. Record the actual count and any genuine shared-environment issue in evaluation documentation.

- [ ] **Step 2: Run representative CLI paths.**

```powershell
python main.py ask --question "报销凭证多久提交？" --database data/final-check.db
python main.py ask --question "普通国内差旅报销凭证多久提交？" --database data/final-check.db
```

Expected: first returns cited conflict clarification; second returns cited D01 answer; both traces include safe retrieval diagnostics. Remove the database afterward.

- [ ] **Step 3: Verify hygiene and commit the tested state.**

```powershell
git check-ignore -v .env data/final-check.db
git status --short -- xiaoying-q3-enterprise-knowledge-qa-agent
git add -- xiaoying-q3-enterprise-knowledge-qa-agent
git diff --cached --check
git commit -m "feat(q3): upgrade retrieval to embeddings"
git rev-parse HEAD
```

Expected: no generated database, cache, or secret is staged.
