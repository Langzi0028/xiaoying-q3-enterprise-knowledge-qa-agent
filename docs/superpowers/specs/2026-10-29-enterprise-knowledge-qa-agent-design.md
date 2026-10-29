# Enterprise Knowledge QA Agent Design

## Goal

Build a self-contained, runnable CLI agent for assessment question 3. It helps employees find reliable answers from enterprise policy and product knowledge, verifies citations against source chunks, and asks a clarification question rather than guessing when retrieved documents conflict.

## Scope

- A new question-local project directory: `xiaoying-q3-enterprise-knowledge-qa-agent/`.
- Python CLI entry point: `python main.py ask --question "..."`.
- A root-level `enterprise_qa/` application package; no `src/` layout.
- A synthetic, non-secret knowledge base with document IDs, versions, dates, and source chunks.
- Document search and source-chunk reading tools.
- A bounded LangGraph workflow with a model-selected action loop when a configured OpenAI-compatible model is available.
- A deterministic, explicitly labelled fallback planner for missing or failed model configuration.
- SQLite storage for run audit records and LangGraph checkpoints.
- JSON final results on stdout, short notices only on stderr.
- Executable regression tests, reproducible examples, and the required assessment documentation.

## Non-goals

- Web UI, HTTP API, authentication, authorization, external document providers, production databases, document uploads, or real enterprise credentials.
- Claiming fallback output proves live-model decision quality.
- Storing prompts containing private information, credentials, model headers, or gateway URLs in traces or examples.

## User Flow

1. An employee invokes the CLI with a question and optional conversation ID.
2. The workflow validates the input and searches the synthetic knowledge base.
3. The planner chooses a permitted next action based on the current observable state.
4. The selected tool executes and returns a safe summary to the workflow.
5. The planner observes the tool result and either reads evidence, answers with citations, asks a clarification question, or stops.
6. The final JSON result and a redacted, inspectable trace are persisted in SQLite and printed on stdout.

## Knowledge Base And Evidence Rules

The project includes the following safe fixtures:

- `D01`, Travel and Expense Policy, version 2026.1, which says ordinary domestic travel receipts must be submitted within 30 calendar days.
- `D02`, Urgent Project Expense Addendum, version 2026.2, which says urgent-project reimbursements have a 15-day deadline but requires confirmation of the request's project scope.
- Additional product and support documents to exercise unambiguous answers, reformulated questions, and contextual follow-up questions.

Search results include the document ID, version, date, title, source chunk ID, and a short excerpt. `read_chunk` returns the complete synthetic source chunk. An answer may cite only chunks read during the same run. The answer builder must use the verified source text and retain the cited document ID, version, chunk ID, and date.

If D01 and D02 both apply but the employee did not specify whether the expense belongs to an urgent project, the agent must return a clarification question that explains the two deadlines and their cited sources. It must not choose either deadline.

## Workflow And Model Boundary

The LangGraph state includes the question, conversation context, search hits, read chunks, observed tool results, trace, tool-call count, and final result.

The workflow has these nodes:

```text
validate_input
-> choose_action
-> execute_action
-> observe_result
-> choose_action | finalize
```

`choose_action` can select only one of these action names:

- `search_documents`
- `read_chunk`
- `ask_clarifying_question`
- `answer_with_citations`
- `stop`

The optional live model receives only a constrained decision request and must emit a validated action object. It cannot execute tools, write storage, select arbitrary citations, or change execution limits. The application validates model output against the currently allowed action set and available safe IDs before any execution.

If `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or `OPENAI_MODEL` is absent, the workflow uses a deterministic rule planner and labels the result and trace `decision_source: "fallback_missing_config"`. If a configured model call fails or returns invalid structured output, the workflow writes only the exception class to stderr, falls back for that decision, and labels the path `fallback_live_error` or `fallback_invalid_output`. A successful online decision records `decision_source: "live_llm"` without storing credentials, headers, full prompts, or the gateway URL.

The workflow permits at most 8 action/tool steps. On reaching the limit, it finalizes with `status: "incomplete"` and `error_code: "EXECUTION_LIMIT_REACHED"`; it must not loop or claim a complete answer.

## Output Contract

The final stdout object has this stable high-level structure:

```json
{
  "status": "answered | clarification_required | not_found | incomplete | invalid_request | tool_failed",
  "answer": "string or null",
  "clarifying_question": "string or null",
  "citations": [
    {
      "document_id": "D01",
      "version": "2026.1",
      "date": "2026-01-01",
      "chunk_id": "D01-C1",
      "title": "Travel and Expense Policy"
    }
  ],
  "decision_source": "live_llm | fallback_missing_config | fallback_live_error | fallback_invalid_output",
  "trace": [],
  "error_code": "string or null"
}
```

Each trace record contains `step`, `node`, `action`, safe `parameters`, a short `result_summary`, `next_action`, `decision_source`, and a concise externally safe rationale. It never contains a chain of thought, secret, raw model prompt, raw model response, private URL, or generated database contents.

## Error Handling

- Empty or whitespace-only questions return `invalid_request` before a tool call.
- No search results return `not_found` with a short statement that no source material supports an answer.
- A document-read or search-tool error returns `tool_failed` or follows a valid alternate action; the trace retains the safe failure summary.
- A model error uses the fallback path as described above.
- A missing or stale citation is rejected during validation; the answer node cannot produce a final answer without at least one verified chunk.

## Persistence

SQLite persists safe run metadata, trace records, and LangGraph checkpoints in a question-local runtime database. The database is generated at runtime and ignored by Git. Conversation IDs allow a later question such as "那紧急项目呢？" to use the previous cited subject, but the response is still based on a new search and chunk-read verification.

## Validation And Evidence

Tests are written first and cover:

- A clear policy question that produces a verified cited answer.
- The 30-day vs. 15-day conflict that produces clarification instead of a guessed deadline.
- A question outside the knowledge base.
- A reformulated question that retrieves the same supported rule.
- A follow-up question using a conversation ID.
- Empty input, forced tool failure, invalid live-model action data, and execution-limit exhaustion.

`examples/` contains at least three actual input/output/trace evidence sets. The set includes two different action paths caused by different observed tool results, including the conflict/clarification path. A live-model evidence file is generated only if local configuration supports a real online call; otherwise the evaluation documentation explicitly marks it unavailable.

## Contract Impact

This creates a new, question-local CLI and persistence contract only. It does not modify any existing question, API, database schema, storage protocol, permission model, external service, or environment contract. The new environment variable names are documented without values in `.env.example`.

## Acceptance Criteria

- The program runs from the question root with `python main.py ask --question "..."`.
- A supported answer uses a source chunk verified in that run and includes complete citation metadata.
- Conflicting policy sources result in a cited clarification question, never an arbitrary answer.
- The trace shows a bounded action loop with action changes derived from observed tool results.
- Missing and failed model configuration uses a transparent fallback without leaking sensitive values.
- Tests and examples demonstrate normal, conflict, unsupported-material, reformulated, contextual, error, and limit behavior.
- All required repository materials exist in the question-local folder and no generated database, `.env`, cache, or secret is included in the delivery.
