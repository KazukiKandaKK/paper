from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from paper2exp.core.run.runner import Runner


@dataclass
class ValidationResult:
    url: str
    status: str
    stdout_tail: str
    stderr_tail: str


def classify_git_error(exit_code: int | None, stderr: str) -> str:
    if exit_code == 0:
        return "ok"
    stderr_l = (stderr or "").lower()
    if "repository not found" in stderr_l or "not found" in stderr_l:
        return "not_found"
    if "permission denied" in stderr_l or "authentication" in stderr_l or "could not read username" in stderr_l:
        return "auth_or_permission"
    if "could not resolve host" in stderr_l or "timed out" in stderr_l or "timeout" in stderr_l:
        return "network_error"
    return "network_error"


def validate_candidates(
    candidates: Iterable[str],
    runner: Runner,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for url in candidates:
        record = runner.run(
            ["env", "GIT_TERMINAL_PROMPT=0", "git", "ls-remote", url],
            cwd=runner.logs_dir.parent,
            timeout_sec=20,
        )
        status = classify_git_error(record.get("exit_code"), record.get("stderr_tail", ""))
        results.append(
            ValidationResult(
                url=url,
                status=status,
                stdout_tail=record.get("stdout_tail", ""),
                stderr_tail=record.get("stderr_tail", ""),
            )
        )
    return results
