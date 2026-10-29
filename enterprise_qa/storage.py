"""SQLite persistence for safe run records and short conversation context."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Storage:
    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    final_result TEXT NOT NULL,
                    trace TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversation_subjects (
                    conversation_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    state_summary TEXT NOT NULL,
                    PRIMARY KEY (run_id, step)
                );
                """
            )

    def record_run(
        self, run_id: str, final_result: dict[str, Any], trace: list[dict[str, Any]]
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO runs (run_id, final_result, trace) VALUES (?, ?, ?)",
                (run_id, json.dumps(final_result, ensure_ascii=False), json.dumps(trace, ensure_ascii=False)),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT final_result, trace FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return {"final_result": json.loads(row[0]), "trace": json.loads(row[1])}

    def save_conversation_subject(self, conversation_id: str, subject: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO conversation_subjects (conversation_id, subject) VALUES (?, ?)",
                (conversation_id, subject),
            )

    def get_conversation_subject(self, conversation_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT subject FROM conversation_subjects WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        return row[0] if row else None

    def checkpoint(self, run_id: str, step: int, state_summary: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO checkpoints (run_id, step, state_summary) VALUES (?, ?, ?)",
                (run_id, step, json.dumps(state_summary, ensure_ascii=False)),
            )
