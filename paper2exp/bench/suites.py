from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Sequence

from paper2exp.core.build.env import build_env, venv_python
from paper2exp.core.models import ExperimentSpec
from paper2exp.core.run.runner import Runner
from paper2exp.core.run.smoke import select_smoke_command
from paper2exp.core.utils import write_text


def stability_3seeds(spec: ExperimentSpec, runner: Runner, cwd: Path) -> dict:
    main_run = spec.repro.runs[0] if spec.repro.runs else None
    if not main_run or not main_run.seeds:
        return {"status": "skipped", "reason": "no seeds in spec"}
    seeds = main_run.seeds[:3]
    results = []
    for seed in seeds:
        cmd = main_run.command + ["--seed", str(seed)]
        res = runner.run(cmd, cwd=cwd)
        results.append({"seed": seed, "exit_code": res.get("exit_code")})
    return {"status": "ok", "runs": results}


def cost_profile(results_path: Path) -> dict:
    if not results_path.exists():
        return {"status": "skipped", "reason": "no results"}
    last = None
    for line in results_path.read_text(encoding="utf-8").splitlines():
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    if not last:
        return {"status": "skipped", "reason": "no records"}
    return {
        "status": "ok",
        "duration_sec": last.get("duration_sec"),
        "exit_code": last.get("exit_code"),
        "rss_kb": None,
    }


def rerun_clean(
    run_dir: Path,
    code_dir: Path,
    runner: Runner,
    no_exec: bool,
) -> dict:
    venv_dir = run_dir / ".venv"
    if no_exec:
        return {"status": "skipped", "reason": "no-exec"}
    if venv_dir.exists():
        shutil.rmtree(venv_dir, ignore_errors=True)
    build_env(run_dir, code_dir, runner, no_exec=False)
    smoke_cmd = select_smoke_command(code_dir, venv_python(venv_dir))
    res = runner.run(smoke_cmd, cwd=code_dir)
    return {"status": "ok", "exit_code": res.get("exit_code")}


def run_benchmarks(
    spec: ExperimentSpec,
    run_dir: Path,
    code_dir: Path,
    smoke_cmd: Sequence[str],
    runner: Runner,
    no_exec: bool,
) -> dict:
    results = {}
    for suite in spec.bench.suites:
        if suite == "stability_3seeds":
            results[suite] = stability_3seeds(spec, runner, cwd=code_dir)
        elif suite == "cost_profile":
            results[suite] = cost_profile(run_dir / "repro" / "results.jsonl")
        elif suite == "rerun_clean":
            results[suite] = rerun_clean(run_dir, code_dir, runner, no_exec)
        else:
            results[suite] = {"status": "skipped", "reason": "unknown suite"}
    report_lines = ["# Bench Report", ""]
    for name, result in results.items():
        report_lines.append(f"## {name}")
        report_lines.append("```json")
        report_lines.append(json.dumps(result, separators=(",", ":")))
        report_lines.append("```")
        report_lines.append("")
    write_text(run_dir / "bench" / "report.md", "\n".join(report_lines))
    (run_dir / "bench" / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    return results
