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
) -> None:
    run_rel = Path("runs") / run_dir.name
    lines = ["# Run Summary", ""]
    lines.append(f"Paper: {spec.paper.id}")
    lines.append(f"Title: {spec.paper.title}")
    lines.append("")
    lines.append("## Status")
    lines.append(f"- repo_cloned: {repo_ok}")
    lines.append(f"- exec_ok: {exec_ok}")
    if notes:
        lines.append(f"- notes: {notes}")
    lines.append("")
    lines.append("## Paths")
    lines.append(f"- paper: {run_rel / 'paper'}")
    lines.append(f"- repro: {run_rel / 'repro'}")
    lines.append(f"- bench: {run_rel / 'bench'}")
    write_text(run_dir / "summary.md", "\n".join(lines))
