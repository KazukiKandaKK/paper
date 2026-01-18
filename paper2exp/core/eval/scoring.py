from __future__ import annotations

import json
from pathlib import Path

from paper2exp.core.models import ExperimentSpec
from paper2exp.core.utils import write_text


def load_last_result(results_path: Path) -> dict | None:
    if not results_path.exists():
        return None
    last = None
    for line in results_path.read_text(encoding="utf-8").splitlines():
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    return last


def write_compare(
    spec: ExperimentSpec,
    run_dir: Path,
    rerun_ok: bool | None,
    exec_ok_override: bool | None = None,
) -> dict:
    last = load_last_result(run_dir / "repro" / "results.jsonl")
    exec_ok = bool(last and last.get("exit_code") == 0)
    if exec_ok_override is not None:
        exec_ok = bool(exec_ok_override)
    format_ok = True
    compare = {
        "format_ok": format_ok,
        "exec_ok": exec_ok,
        "rerun_ok": rerun_ok,
        "notes": "",
    }
    lines = ["# Reproduction Compare", "", "| Metric | Value |", "|---|---|"]
    for key in ["format_ok", "exec_ok", "rerun_ok"]:
        lines.append(f"| {key} | {compare.get(key)} |")
    if spec.eval.target_metrics:
        lines.append("\nTarget metrics (not implemented):")
        for metric in spec.eval.target_metrics:
            lines.append(f"- {metric}")
    write_text(run_dir / "repro" / "compare.md", "\n".join(lines))
    return compare
