from __future__ import annotations

import json
from pathlib import Path

import yaml

from paper2exp.core.utils import write_text


def write_paper_to_code_artifacts(
    run_dir: Path,
    *,
    paper_text: str,
    llm_response_path: Path | None = None,
) -> None:
    out_dir = run_dir / "paper_to_code"
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence_items: list[dict] = []
    missing_info: list[str] = []
    if llm_response_path and llm_response_path.exists():
        try:
            response = json.loads(llm_response_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            response = {}
        evidence_items = [
            item for item in response.get("evidence", []) if isinstance(item, dict)
        ]
        missing_info = [
            item for item in response.get("missing_info", []) if isinstance(item, str)
        ]

    plan_md = _render_plan(evidence_items, missing_info, paper_text)
    todo_md = _render_todo(missing_info)

    write_text(out_dir / "plan.md", plan_md)
    write_text(out_dir / "todo.md", todo_md)

    patch_path = out_dir / "spec_patch.yaml"
    patch_path.write_text(yaml.safe_dump({}, sort_keys=False), encoding="utf-8")


def _render_plan(evidence_items: list[dict], missing_info: list[str], paper_text: str) -> str:
    lines = ["# Paper-to-Code Plan", ""]
    lines.append("## Confirmed Facts (evidence)")
    if evidence_items:
        for item in evidence_items[:25]:
            locator = str(item.get("locator", "")).strip()
            quote = str(item.get("quote", "")).strip()
            if not quote:
                continue
            prefix = f"[{locator}] " if locator else ""
            lines.append(f"- {prefix}{quote}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Unknown / Missing Info")
    if missing_info:
        for item in missing_info:
            if item.strip():
                lines.append(f"- {item.strip()}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Evidence-bound: unknown items remain empty.")
    if not paper_text:
        lines.append("- Paper text unavailable; no evidence extracted.")
    return "\n".join(lines).strip() + "\n"


def _render_todo(missing_info: list[str]) -> str:
    lines = ["# Paper-to-Code TODO", ""]
    lines.append("- [ ] Confirm official repository URL if available (use --repo-url).")
    lines.append("- [ ] Locate reproducibility steps in the paper or appendix.")
    lines.append("- [ ] Identify datasets and preprocessing (if specified).")
    lines.append("- [ ] Identify model architecture and training procedure.")
    lines.append("- [ ] Draft minimal training/evaluation scripts once evidence is available.")
    if missing_info:
        lines.append("")
        lines.append("## Missing Info (from LLM)")
        for item in missing_info:
            if item.strip():
                lines.append(f"- {item.strip()}")
    return "\n".join(lines).strip() + "\n"
