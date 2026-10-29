# Xiaoying Q3 Enterprise Knowledge QA Agent

A self-contained Python CLI for the third Xiaoying assessment question: enterprise knowledge Q&A with source verification, conflict clarification, safe fallback, bounded actions, and auditable traces.

## Review Entry Point

1. Read `docs/01-requirements.md`, `docs/02-solution.md`, and `docs/03-evaluation.md`.
2. Run the full suite from this directory: `python -m pytest -v`.
3. Inspect the actual request/output/trace evidence in `examples/`.
4. Start with the conflict path:

```powershell
python main.py ask --question "报销凭证多久提交？" --database data/review.db
```

It returns `clarification_required` with the 30-day D01 and 15-day D02 citations because the request does not state whether the expense belongs to an urgent project.

## Installation and Run

Run these commands from `xiaoying-q3-enterprise-knowledge-qa-agent/` using the selected Conda/PyCharm interpreter:

```powershell
python -m pip install -r requirements.txt
python main.py ask --question "普通国内差旅报销凭证多久提交？"
python -m pytest -v
```

The direct entry point is only `python main.py`. The project uses the repository-required root package `enterprise_qa/` rather than a `src/` layout.

## CLI Contract

```powershell
python main.py ask --question "..." [--conversation-id ID] [--database PATH] [--max-steps N]
```

The final machine-readable JSON is written to stdout. Short notices about missing model configuration or a model exception type are written to stderr. Trace records include node, action, safe parameters, safe result summary, next action, decision source, and concise rationale. They never include credentials, full prompts, raw responses, private URLs, or model chain-of-thought.

## Model Configuration

Copy `.env.example` to `.env` and supply all three variable values only in your local environment:

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
```

Shell/PyCharm values take precedence. With no complete configuration, the program writes a concise stderr notice and uses `fallback_missing_config`. With a configured model, it makes a bounded action-selection request; it records `live_llm` only after a validated online response. Failed or invalid live decisions fall back safely and never disclose the credential or gateway details.

## Known Limitations and No-Secret Policy

- All documents are safe synthetic fixtures; this is not a production enterprise document service.
- The local fallback validates workflow boundaries but is not presented as proof of live-model quality.
- During the recorded verification no complete model configuration was available; see `examples/04-live-llm-evidence.md`.
- Never commit `.env`, API keys, tokens, passwords, private URLs, generated SQLite databases, virtual environments, caches, or IDE metadata.
