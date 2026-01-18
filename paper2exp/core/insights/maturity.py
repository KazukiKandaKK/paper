from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Maturity:
    level: str
    reason: str


def compute_maturity(
    run_dir: Path,
    repo_cloned: bool,
    paper_to_code_generated: bool,
) -> Maturity:
    records = _load_results(run_dir / "repro" / "results.jsonl")
    smoke_success = _has_smoke_success(records)
    pytest_success = _has_pytest_success(records)
    any_success = any(rec.get("exit_code") == 0 for rec in records)

    if pytest_success:
        return Maturity(level="L2_TESTS", reason="pytest succeeded")
    if smoke_success or any_success:
        return Maturity(level="L1_SMOKE", reason="at least one command succeeded")
    if not repo_cloned and paper_to_code_generated:
        return Maturity(level="L0_NOT_RUNNABLE", reason="repo unavailable; paper-to-code fallback only")
    if not repo_cloned:
        return Maturity(level="L0_NOT_RUNNABLE", reason="repo not cloned")
    return Maturity(level="L0_NOT_RUNNABLE", reason="no successful execution")


def _load_results(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _has_smoke_success(records: list[dict]) -> bool:
    for rec in records:
        cmd = " ".join(rec.get("command", []))
        if rec.get("exit_code") == 0 and "smoke ok" in (rec.get("stdout_tail") or "").lower():
            return True
        if rec.get("exit_code") == 0 and "-c" in cmd and "smoke ok" in cmd:
            return True
    return False


def _has_pytest_success(records: list[dict]) -> bool:
    for rec in records:
        cmd = " ".join(rec.get("command", []))
        if rec.get("exit_code") == 0 and "pytest" in cmd:
            return True
    return False
