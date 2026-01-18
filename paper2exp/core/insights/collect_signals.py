from __future__ import annotations

import json
from pathlib import Path

from paper2exp.core.utils import truncate_text


def collect_signals(run_dir: Path) -> list[dict]:
    signals: list[dict] = []
    counter = 1

    def add_signal(source: str, locator: str, quote: str) -> None:
        nonlocal counter
        quote = truncate_text(quote.strip(), max_chars=500)
        if not quote:
            return
        signals.append(
            {
                "id": f"S{counter}",
                "source": source,
                "locator": truncate_text(locator, max_chars=200),
                "quote": quote,
            }
        )
        counter += 1

    summary_path = run_dir / "summary.md"
    if summary_path.exists():
        for idx, line in enumerate(
            summary_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.startswith(("Paper:", "Title:", "- repo_cloned", "- repro_executed", "- repro_verified")):
                add_signal("summary", f"summary.md:{idx}", line)
            elif line.startswith("- notes:"):
                add_signal("summary", f"summary.md:{idx}", line)
            elif line.startswith("Official reproduction:") or line.startswith("Reason:"):
                add_signal("summary", f"summary.md:{idx}", line)

    validation_path = run_dir / "repo" / "validation.json"
    if validation_path.exists():
        try:
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            validation = {}
        for idx, item in enumerate(validation.get("results", []), start=1):
            quote = f"status={item.get('status')} stderr={item.get('stderr_tail', '')}".strip()
            add_signal("repo_validation", f"repo/validation.json:{idx}", quote)

    results_path = run_dir / "repro" / "results.jsonl"
    if results_path.exists():
        lines = results_path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines[-5:], start=max(len(lines) - 4, 1)):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            cmd = " ".join(record.get("command", []))
            quote = f"cmd={cmd} exit_code={record.get('exit_code')} stderr={record.get('stderr_tail','')}"
            add_signal("results_jsonl", f"repro/results.jsonl:{idx}", quote)

    bench_path = run_dir / "bench" / "report.md"
    if bench_path.exists():
        for idx, line in enumerate(bench_path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("{\"status\"") or line.startswith("## "):
                add_signal("bench_report", f"bench/report.md:{idx}", line)

    plan_path = run_dir / "paper_to_code" / "plan.md"
    if plan_path.exists():
        for idx, line in enumerate(plan_path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("- "):
                add_signal("paper_to_code", f"paper_to_code/plan.md:{idx}", line)

    todo_path = run_dir / "paper_to_code" / "todo.md"
    if todo_path.exists():
        for idx, line in enumerate(todo_path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("- ["):
                add_signal("paper_to_code", f"paper_to_code/todo.md:{idx}", line)

    metadata_path = run_dir / "paper" / "metadata.json"
    if metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
        if meta.get("id"):
            add_signal("metadata", "paper/metadata.json:id", f"id={meta.get('id')}")
        if isinstance(meta.get("links"), dict):
            for key, value in meta["links"].items():
                if value:
                    add_signal("metadata", f"paper/metadata.json:links:{key}", f"{key}={value}")

    return signals
