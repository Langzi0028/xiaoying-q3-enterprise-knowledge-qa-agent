# Enterprise Knowledge QA Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a runnable, bounded enterprise knowledge Q&A CLI agent that verifies source chunks and asks clarification questions for policy conflicts.

**Architecture:** A root Python package contains the synthetic knowledge base, retrieval tools, constrained planner, LangGraph action loop, and SQLite audit storage. The CLI parses arguments and prints the final JSON only; deterministic guards validate every selected action, citation, and termination path.

**Tech Stack:** Python 3.11+, LangGraph, SQLite (`sqlite3`), optional `langchain-openai`, `python-dotenv`, pytest.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `main.py` | Direct entry point that calls `enterprise_qa.cli.main()`. |
| `enterprise_qa/models.py` | Typed actions, citations, results, and trace structures. |
| `enterprise_qa/knowledge_base.py` | Synthetic versioned documents and deterministic query ranking. |
| `enterprise_qa/tools.py` | Search and chunk-read business tools with safe failures. |
| `enterprise_qa/planner.py` | Rule fallback, optional live LLM decision, and decision validation. |
| `enterprise_qa/storage.py` | SQLite audit, checkpoint, and safe conversation-subject persistence. |
| `enterprise_qa/workflow.py` | Bounded LangGraph state machine and result/citation guards. |
| `enterprise_qa/cli.py` | Argument parsing, optional `.env`, stderr notices, JSON stdout. |
| `tests/` | Regression and CLI coverage. |
| `examples/` | Actual input, output, and trace evidence. |
| `docs/01-requirements.md` - `docs/05-retrospective.md` | Required assessment documentation. |

### Task 1: Create the question-local scaffold and safe CLI boundary

**Files:**
- Create: `main.py`
- Create: `enterprise_qa/__init__.py`
- Create: `enterprise_qa/cli.py`
- Create: `README.md`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `data/.gitkeep`
- Create: `tests/test_cli.py`

- [x] **Step 1: Write the failing CLI contract test.**

```python
def test_cli_returns_json_and_missing_llm_notice(tmp_path):
    completed = run_cli([
        "ask", "--question", "报销凭证多久提交？",
        "--database", str(tmp_path / "q3.db"),
    ])
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "answered"
    assert "LLM configuration missing" in completed.stderr
```

- [x] **Step 2: Run it from the question root to verify it fails.**

```powershell
Set-Location xiaoying-q3-enterprise-knowledge-qa-agent
python -m pytest tests/test_cli.py::test_cli_returns_json_and_missing_llm_notice -v
```

Expected: FAIL because the application does not exist.

- [x] **Step 3: Implement the minimal entry point and `ask` parser.**

`main.py` imports and calls `enterprise_qa.cli.main()` only. Parse `--question`, `--conversation-id`, `--database`, `--max-steps`, and a test-only safe tool-failure option. Reserve stdout for one JSON object and stderr for notices.

- [x] **Step 4: Add configuration and ignore rules.**

Declare LangGraph, `langchain-openai`, `python-dotenv`, and pytest. Put only `OPENAI_API_KEY=`, `OPENAI_BASE_URL=`, and `OPENAI_MODEL=` in `.env.example`. Ignore `.env`, IDE/venv/cache artifacts, and generated local databases.

- [x] **Step 5: Commit the scaffold.**

```powershell
git add -- main.py enterprise_qa README.md requirements.txt .env.example .gitignore data/.gitkeep tests/test_cli.py
git commit -m "chore(q3): scaffold enterprise QA agent"
```

### Task 2: Build typed knowledge fixtures and safe retrieval tools

**Files:**
- Create: `enterprise_qa/models.py`
- Create: `enterprise_qa/knowledge_base.py`
- Create: `enterprise_qa/tools.py`
- Create: `tests/test_knowledge_base.py`
- Create: `tests/test_tools.py`

- [x] **Step 1: Write failing retrieval tests.**

```python
def test_search_returns_both_conflicting_expense_documents():
    results = search_documents("报销凭证多久提交？")
    assert {result.document_id for result in results} == {"D01", "D02"}


def test_read_chunk_returns_versioned_primary_source_text():
    chunk = read_chunk("D01-C1")
    assert chunk.document_id == "D01"
    assert chunk.version == "2026.1"
    assert "30" in chunk.text
```

- [x] **Step 2: Verify the tests fail.**

```powershell
python -m pytest tests/test_knowledge_base.py tests/test_tools.py -v
```

Expected: FAIL because the data and tools are not implemented.

- [x] **Step 3: Add data structures.**

Define dataclasses for documents, chunks, actions, citations, traces, tool results, planner decisions, and final results. Include safe `to_dict()` serialization only; it must never serialize secrets, model request data, or private URLs.

- [x] **Step 4: Add safe fixture data and deterministic ranking.**

Create D01 (`2026.1`, ordinary domestic travel receipts, 30 days), D02 (`2026.2`, urgent project reimbursement, 15 days and scope requirement), and limited product/support fixtures. Add Chinese synonym handling for the stated reformulation tests. Search results expose only ID, title, version, date, chunk ID, and brief excerpt.

- [x] **Step 5: Implement `search_documents` and `read_chunk`.**

Return structured safe results and support injected named failures for tests without mocks. Use safe error codes such as `SEARCH_UNAVAILABLE`, `READ_UNAVAILABLE`, and `CHUNK_NOT_FOUND`.

- [x] **Step 6: Run and commit the focused suite.**

```powershell
python -m pytest tests/test_knowledge_base.py tests/test_tools.py -v
git add -- enterprise_qa/models.py enterprise_qa/knowledge_base.py enterprise_qa/tools.py tests/test_knowledge_base.py tests/test_tools.py
git commit -m "feat(q3): add verifiable knowledge retrieval tools"
```

Expected: PASS.

### Task 3: Add safe SQLite run and conversation persistence

**Files:**
- Create: `enterprise_qa/storage.py`
- Create: `tests/test_storage.py`
- Modify: `.gitignore`

- [x] **Step 1: Write failing persistence tests.**

```python
def test_run_persists_redacted_trace_and_final_result(tmp_path):
    storage = Storage(tmp_path / "audit.db")
    storage.record_run("run-1", final_result, trace)
    assert storage.get_run("run-1")["final_result"]["status"] == "answered"


def test_conversation_context_returns_only_previous_safe_subject(tmp_path):
    storage = Storage(tmp_path / "audit.db")
    storage.save_conversation_subject("conv-1", "reimbursement deadline")
    assert storage.get_conversation_subject("conv-1") == "reimbursement deadline"
```

- [x] **Step 2: Verify failure, then implement.**

```powershell
python -m pytest tests/test_storage.py -v
```

Use `sqlite3` to create idempotent tables for run metadata, trace JSON, final result JSON, safe conversation subject, and checkpoint metadata. Explicitly omit credentials, prompt bodies, raw model output, headers, and gateway URLs.

- [x] **Step 3: Re-run tests and commit.**

```powershell
python -m pytest tests/test_storage.py -v
git add -- enterprise_qa/storage.py tests/test_storage.py .gitignore
git commit -m "feat(q3): persist redacted run audit records"
```

Expected: PASS and generated `data/*.db` / `data/*.sqlite` remain ignored.

### Task 4: Implement the constrained planner and live-model boundary

**Files:**
- Create: `enterprise_qa/planner.py`
- Create: `tests/test_planner.py`
- Modify: `enterprise_qa/models.py`

- [x] **Step 1: Write failing planner tests.**

```python
def test_missing_config_uses_explicit_rule_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    decision = Planner.from_environment().choose(state)
    assert decision.source == "fallback_missing_config"
    assert decision.action.name == "search_documents"


def test_invalid_live_action_is_rejected_and_falls_back():
    planner = Planner.with_test_response({"action": "delete_database"})
    decision = planner.choose(state)
    assert decision.source == "fallback_invalid_output"
    assert decision.action.name in ALLOWED_ACTIONS
```

- [x] **Step 2: Verify failure.**

```powershell
python -m pytest tests/test_planner.py -v
```

- [x] **Step 3: Implement the rule fallback.**

Choose search first, then chunk reads, then clarification for the D01/D02 conflict with missing urgent-project scope, answer only after verified source reads, and stop on no results or unrecoverable tool failure. This deterministic branch is explicitly a fallback/boundary validator.

- [x] **Step 4: Implement and validate optional live decisions.**

Load `.env` without overriding process environment. Call the configured model only when all three variables are present and only for one constrained allowed-action object. Validate action names and parameters against the current state before dispatch. Map failed requests to `fallback_live_error` and malformed model objects to `fallback_invalid_output`; surface only the exception class via the CLI notice mechanism.

- [x] **Step 5: Run and commit.**

```powershell
python -m pytest tests/test_planner.py -v
git add -- enterprise_qa/planner.py enterprise_qa/models.py tests/test_planner.py
git commit -m "feat(q3): add bounded action planner with live fallback"
```

Expected: PASS.

### Task 5: Build the bounded LangGraph loop and citation/result guards

**Files:**
- Create: `enterprise_qa/workflow.py`
- Create: `tests/test_workflow.py`
- Modify: `enterprise_qa/tools.py`
- Modify: `enterprise_qa/storage.py`
- Modify: `enterprise_qa/cli.py`

- [x] **Step 1: Write failing end-to-end workflow tests.**

```python
def test_clear_question_answers_only_with_a_chunk_read_in_this_run(tmp_path):
    result = run_question("普通国内差旅报销凭证多久提交？", database=tmp_path / "q3.db")
    assert result.status == "answered"
    assert result.citations[0].document_id == "D01"
    assert any(item.action == "read_chunk" for item in result.trace)


def test_conflicting_deadlines_require_scope_clarification(tmp_path):
    result = run_question("报销凭证多久提交？", database=tmp_path / "q3.db")
    assert result.status == "clarification_required"
    assert result.answer is None
    assert {item.document_id for item in result.citations} == {"D01", "D02"}


def test_limit_exhaustion_is_explicitly_incomplete(tmp_path):
    result = run_question("报销凭证多久提交？", database=tmp_path / "q3.db", max_steps=1)
    assert result.status == "incomplete"
    assert result.error_code == "EXECUTION_LIMIT_REACHED"
```

- [x] **Step 2: Verify failure.**

```powershell
python -m pytest tests/test_workflow.py -v
```

- [x] **Step 3: Build LangGraph nodes.**

Create `validate_input`, `choose_action`, `execute_action`, `observe_result`, and `finalize` nodes with conditional routing. Enforce `max_steps` before each execution and persist a safe checkpoint after each state transition.

- [x] **Step 4: Build trace records and action dispatch.**

Map only validated actions to tools or guarded finish actions. Every trace record contains node, action, safe parameters, result summary, next action, decision source, and concise safe rationale. Retain observed failures and ensure they cause a visible action change or final safe failure.

- [x] **Step 5: Build citation and outcome guards.**

A normal answer requires one or more chunks read in the same run and exact citation metadata from those chunks. A conflict clarification requires D01/D02 reads and cites both. Invalid input must produce zero actions; no results produce `not_found`; unrecoverable tool error produces `tool_failed`; exhausted steps produce `incomplete` with `EXECUTION_LIMIT_REACHED`.

- [x] **Step 6: Wire the CLI, run tests, and commit.**

```powershell
python -m pytest tests/test_workflow.py tests/test_cli.py -v
git add -- enterprise_qa/workflow.py enterprise_qa/tools.py enterprise_qa/storage.py enterprise_qa/cli.py tests/test_workflow.py tests/test_cli.py
git commit -m "feat(q3): add auditable bounded knowledge QA workflow"
```

Expected: PASS with JSON-only stdout and concise stderr fallback notice.

### Task 6: Add all remaining regression behavior before documentation

**Files:**
- Create: `tests/test_regressions.py`
- Modify: `enterprise_qa/workflow.py`
- Modify: `enterprise_qa/planner.py`
- Modify: `enterprise_qa/knowledge_base.py`

- [x] **Step 1: Write the failing edge-case suite.**

```python
def test_unrelated_question_reports_not_found(tmp_path):
    assert run_question("公司股票什么时候上市？", database=tmp_path / "q3.db").status == "not_found"


def test_reformulated_question_still_returns_d01(tmp_path):
    result = run_question("国内出差的发票最迟几天交？", database=tmp_path / "q3.db")
    assert result.citations[0].document_id == "D01"


def test_follow_up_question_uses_safe_conversation_subject(tmp_path):
    database = tmp_path / "q3.db"
    run_question("普通差旅报销的期限？", database=database, conversation_id="c1")
    result = run_question("那紧急项目呢？", database=database, conversation_id="c1")
    assert result.citations[0].document_id == "D02"


def test_search_failure_is_safe_and_does_not_claim_an_answer(tmp_path):
    result = run_question("报销凭证多久提交？", database=tmp_path / "q3.db", fail_tool="search_documents")
    assert result.status == "tool_failed"
    assert result.answer is None
```

Also cover whitespace-only input, a one-time chunk read failure, invalid live output, and no duplicate repeat of a prior successful action.

- [x] **Step 2: Run the suite to verify failure.**

```powershell
python -m pytest tests/test_regressions.py -v
```

- [x] **Step 3: Make the smallest required fixes.**

Add only query normalization, safe conversation subject resolution, and failure routing needed to pass. Do not add broad product behavior or unrelated abstraction.

- [x] **Step 4: Re-run and commit.**

```powershell
python -m pytest tests/test_regressions.py -v
git add -- enterprise_qa/workflow.py enterprise_qa/planner.py enterprise_qa/knowledge_base.py tests/test_regressions.py
git commit -m "test(q3): cover conflict and tool failure regressions"
```

Expected: PASS.

### Task 7: Generate actual evidence and assessment documentation

**Files:**
- Create: `examples/01-clear-policy-input.json`
- Create: `examples/01-clear-policy-output.json`
- Create: `examples/01-clear-policy-trace.json`
- Create: `examples/02-conflict-clarification-input.json`
- Create: `examples/02-conflict-clarification-output.json`
- Create: `examples/02-conflict-clarification-trace.json`
- Create: `examples/03-not-found-input.json`
- Create: `examples/03-not-found-output.json`
- Create: `examples/03-not-found-trace.json`
- Create: `examples/04-live-llm-evidence.md`
- Create: `docs/01-requirements.md`
- Create: `docs/02-solution.md`
- Create: `docs/03-evaluation.md`
- Create: `docs/04-ai-usage.md`
- Create: `docs/05-retrospective.md`
- Modify: `README.md`

- [x] **Step 1: Generate deterministic evidence by executing actual commands.**

```powershell
python main.py ask --question "普通国内差旅报销凭证多久提交？" --database data/evidence.db
python main.py ask --question "报销凭证多久提交？" --database data/evidence.db
python main.py ask --question "公司股票什么时候上市？" --database data/evidence.db
```

Save each exact safe input, actual final JSON, and actual trace in the matching example files. Do not create imagined outputs. Remove `data/evidence.db` after evidence capture and confirm it remains ignored.

- [x] **Step 2: Attempt real-model evidence only when configuration exists.**

Run one constrained question with real configured variables and record `decision_source: "live_llm"` only if an actual request succeeds. Otherwise record the real unavailable condition or allowed exception class in the evidence and evaluation doc. Never include credentials, private URLs, prompts, headers, or raw responses.

- [x] **Step 3: Write docs strictly from verified facts.**

`01` describes user/goal/scope. `02` describes action loop, component responsibilities, framework limits, and safety boundary. `03` lists actual test output, failures/limits, and links each acceptance claim to examples. `04` records AI assistance and human review. `05` records actual time, unfinished work, risk, learning, and next step. Explain why this project uses the required root package instead of `src/`.

- [x] **Step 4: Update README and commit evidence.**

```powershell
git add -- README.md examples docs
git commit -m "docs(q3): add evaluation evidence and delivery notes"
```

### Task 8: Verify the complete delivery and commit the tested state

**Files:**
- Modify if necessary: `docs/03-evaluation.md`
- Modify if necessary: `docs/05-retrospective.md`

- [x] **Step 1: Install the declared requirements from the question root.**

```powershell
python -m pip install -r requirements.txt
```

Expected: dependencies resolve or the actual environment incompatibility is documented.

- [x] **Step 2: Run the full suite.**

```powershell
python -m pytest -v
```

Expected: all tests PASS. Record the exact test count and command result in `docs/03-evaluation.md`.

- [x] **Step 3: Run a representative final CLI validation.**

```powershell
python main.py ask --question "报销凭证多久提交？" --database data/final-check.db
```

Expected: `clarification_required`, D01/D02 citations, and at most a concise fallback notice on stderr. Remove the generated database afterward.

- [x] **Step 4: Check delivery hygiene.**

```powershell
git status --short -- xiaoying-q3-enterprise-knowledge-qa-agent
git check-ignore -v .env data/final-check.db
```

Expected: no `.env`, generated database, cache, or secret is staged; only question 3 files are included.

- [x] **Step 5: Commit any verification-note updates and capture the final SHA.**

```powershell
git add -- docs/03-evaluation.md docs/05-retrospective.md
git commit -m "test(q3): record final verification"
git rev-parse HEAD
```

Expected: a real commit SHA identifies the exact tested state. Push only when an explicit target GitHub repository is available; otherwise report the missing URL honestly.
