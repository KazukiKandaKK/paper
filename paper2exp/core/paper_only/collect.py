from __future__ import annotations

import json
from pathlib import Path

from paper2exp.core.insights.collect_signals import collect_signals
from paper2exp.core.paper_only.repo_index import index_repo


def collect_run_artifacts(run_dir: Path) -> dict:
    artifacts = {
        "summary": _read_text(run_dir / "summary.md"),
        "validation": _read_json(run_dir / "repo" / "validation.json"),
        "selection": _read_json(run_dir / "repo" / "selection.json"),
        "results": _read_lines(run_dir / "repro" / "results.jsonl"),
        "bench": _read_text(run_dir / "bench" / "report.md"),
        "metadata": _read_json(run_dir / "paper" / "metadata.json"),
        "paper_to_code_plan": _read_text(run_dir / "paper_to_code" / "plan.md"),
        "paper_to_code_todo": _read_text(run_dir / "paper_to_code" / "todo.md"),
    }
    return artifacts


def collect_signals_for_insights(run_dir: Path) -> list[dict]:
    return collect_signals(run_dir)


def list_paper_repo_files(run_dir: Path) -> list[Path]:
    code_dir = run_dir / "code"
    if not code_dir.exists():
        return []
    return index_repo(code_dir)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()
