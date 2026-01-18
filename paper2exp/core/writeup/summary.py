from __future__ import annotations

from pathlib import Path

from paper2exp.core.models import ExperimentSpec
from paper2exp.core.utils import write_text


def write_summary(
    run_dir: Path,
    spec: ExperimentSpec,
    exec_ok: bool,
    repo_ok: bool,
    notes: str = "",
    repro_executed: bool | None = None,
    repro_verified: bool | None = None,
    paper_to_code_generated: bool | None = None,
    repro_status: str | None = None,
    repro_reason: str | None = None,
    maturity_level: str | None = None,
    maturity_reason: str | None = None,
    pytest_required: bool | None = None,
    pytest_available: bool | None = None,
    pytest_install_attempted: bool | None = None,
    pytest_install_ok: bool | None = None,
    pytest_reason: str | None = None,
) -> None:
    run_rel = Path("runs") / run_dir.name
    lines = ["# Run Summary", ""]
    lines.append(f"Paper: {spec.paper.id}")
    lines.append(f"Title: {spec.paper.title}")
    lines.append("")
    lines.append("## Status")
    lines.append(f"- repo_cloned: {repo_ok}")
    if repro_executed is not None:
        lines.append(f"- repro_executed: {repro_executed}")
    if repro_verified is not None or repro_executed is not None:
        lines.append(f"- repro_verified: {repro_verified}")
    if paper_to_code_generated is not None:
        lines.append(f"- paper_to_code_generated: {paper_to_code_generated}")
    if pytest_required is not None:
        lines.append(f"- pytest_required: {pytest_required}")
    if pytest_available is not None:
        lines.append(f"- pytest_available: {pytest_available}")
    if pytest_install_attempted is not None:
        lines.append(f"- pytest_install_attempted: {pytest_install_attempted}")
    if pytest_install_ok is not None:
        lines.append(f"- pytest_install_ok: {pytest_install_ok}")
    if pytest_reason:
        lines.append(f"- pytest_reason: {pytest_reason}")
    lines.append(f"- exec_ok: {exec_ok} (deprecated; use repro_verified)")
    if notes:
        lines.append(f"- notes: {notes}")
    lines.append("")
    if repro_status or repro_reason:
        lines.append("## Repro status")
        lines.append(
            f"Official reproduction: {repro_status or 'UNKNOWN'}"
        )
        if repro_reason:
            lines.append(f"Reason: {repro_reason}")
        lines.append("")
    if maturity_level or maturity_reason:
        lines.append("## Maturity")
        if maturity_level:
            lines.append(f"- level: {maturity_level}")
        if maturity_reason:
            lines.append(f"- reason: {maturity_reason}")
        lines.append("")
    lines.append("## Paths")
    lines.append(f"- paper: {run_rel / 'paper'}")
    lines.append(f"- repro: {run_rel / 'repro'}")
    lines.append(f"- bench: {run_rel / 'bench'}")
    write_text(run_dir / "summary.md", "\n".join(lines))
