from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReproStatus:
    repo_cloned: bool
    repro_executed: bool
    repro_verified: bool | None
    exec_ok: bool
    paper_to_code_generated: bool
    official_status: str
    reason: str


def load_results(results_path: Path) -> list[dict]:
    if not results_path.exists():
        return []
    records: list[dict] = []
    for line in results_path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def compute_repro_status(run_dir: Path, repo_cloned: bool) -> ReproStatus:
    results_path = run_dir / "repro" / "results.jsonl"
    records = load_results(results_path)
    executed_records = [
        rec
        for rec in records
        if rec.get("status") in {"ran", "timeout"} or rec.get("exit_code") is not None
    ]

    repro_executed = bool(executed_records) and repo_cloned
    last_exit_code = None
    last_cmd = ""
    for rec in reversed(records):
        if rec.get("exit_code") is not None:
            last_exit_code = rec.get("exit_code")
            last_cmd = " ".join(rec.get("command", []))
            break

    pytest_ok = _has_pytest_success(records)
    smoke_ok = _has_smoke_success(records)

    if not repro_executed:
        repro_verified = None
    elif pytest_ok:
        repro_verified = True
    else:
        repro_verified = False

    exec_ok = repro_verified is True
    paper_to_code_generated = (run_dir / "paper_to_code" / "plan.md").exists()
    if not repo_cloned:
        reason = "repo not cloned"
    elif not repro_executed:
        reason = "no execution records"
    elif last_exit_code is None:
        reason = "no exit_code"
    elif pytest_ok:
        reason = "pytest ok"
    elif smoke_ok:
        reason = "smoke ok"
    else:
        reason = f"exit_code {last_exit_code}"

    if not repro_executed:
        official_status = "NOT RUN"
    elif repro_verified:
        official_status = "PASSED"
    else:
        official_status = "FAILED"

    return ReproStatus(
        repo_cloned=repo_cloned,
        repro_executed=repro_executed,
        repro_verified=repro_verified,
        exec_ok=exec_ok,
        paper_to_code_generated=paper_to_code_generated,
        official_status=official_status,
        reason=reason,
    )


def _has_pytest_success(records: list[dict]) -> bool:
    for rec in records:
        cmd = " ".join(rec.get("command", []))
        if rec.get("exit_code") == 0 and "pytest" in cmd:
            return True
    return False


def _has_smoke_success(records: list[dict]) -> bool:
    for rec in records:
        cmd = " ".join(rec.get("command", []))
        stdout = (rec.get("stdout_tail") or "").lower()
        if rec.get("exit_code") == 0 and "smoke ok" in stdout:
            return True
        if rec.get("exit_code") == 0 and "-c" in cmd and "smoke ok" in cmd:
            return True
    return False
