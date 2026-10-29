import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
        environment.pop(key, None)
    return subprocess.run(
        [sys.executable, "main.py", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_returns_json_and_missing_llm_notice(tmp_path: Path) -> None:
    completed = run_cli(
        "ask",
        "--question",
        "报销凭证多久提交？",
        "--database",
        str(tmp_path / "q3.db"),
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "clarification_required"
    assert "LLM configuration missing" in completed.stderr
