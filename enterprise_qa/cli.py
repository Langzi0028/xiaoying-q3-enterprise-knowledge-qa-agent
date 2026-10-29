"""Command-line boundary for the enterprise Q&A agent."""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from .workflow import run_question


def _has_live_llm_config() -> bool:
    return all(
        os.getenv(name)
        for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enterprise knowledge Q&A agent")
    command = parser.add_subparsers(dest="command", required=True)
    ask = command.add_parser("ask", help="Answer an enterprise knowledge question")
    ask.add_argument("--question", required=True)
    ask.add_argument("--conversation-id")
    ask.add_argument("--database", default="data/enterprise_qa.db")
    ask.add_argument("--max-steps", type=int, default=8)
    ask.add_argument("--fail-tool", choices=("search_documents", "read_chunk"))
    return parser


def main() -> None:
    load_dotenv(override=False)
    arguments = build_parser().parse_args()
    from .planner import Planner

    planner = Planner.from_environment()
    result = run_question(
        arguments.question,
        database=arguments.database,
        conversation_id=arguments.conversation_id,
        max_steps=arguments.max_steps,
        fail_tool=arguments.fail_tool,
        planner=planner,
    )
    if not _has_live_llm_config():
        print("LLM configuration missing; using deterministic fallback.", file=sys.stderr)
    elif planner.last_error_type:
        print(
            f"LLM request failed: {planner.last_error_type}; using deterministic fallback.",
            file=sys.stderr,
        )
    if result.embedding_error_type:
        print(
            "Embedding request failed: "
            f"{result.embedding_error_type}; using local vector fallback.",
            file=sys.stderr,
        )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
