# 01 Requirements

## User and goal

Employees need trustworthy answers to enterprise policy and product questions. The agent searches a local synthetic knowledge base, reads the cited source chunks, and returns an answer only when the evidence supports it.

## Scope

- A local Python CLI invoked with `python main.py ask --question "..."`.
- A safe synthetic knowledge base with document IDs, versions, dates, and text chunks.
- Search/read tools, bounded LangGraph orchestration, optional OpenAI-compatible action selection, SQLite audit and checkpoints.
- Cited normal answers, conflict clarification, no-source responses, tool errors, and safe conversation follow-ups.

## Non-goals

No HTTP API, UI, user authorization, external document system, production database, uploaded documents, or real organization data is included.

## Success criteria

- Answers cite chunks read during the current run.
- The 30-day D01 policy and 15-day D02 policy conflict returns a clarification request when urgent-project scope is missing.
- Missing or failing model configuration uses a labelled fallback without exposing configuration values.
- Each run produces a bounded action trace and persists only safe output and trace data.

## Constraints

The local fixtures provide deterministic evaluation coverage; they are not a substitute for a real enterprise document service. A live model run is reported only when a real configured call succeeds.
