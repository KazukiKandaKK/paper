from __future__ import annotations

from pathlib import Path
from typing import Optional

from paper2exp.core.paper_only.applications import build_applications
from paper2exp.core.paper_only.facts import build_facts
from paper2exp.core.paper_only.insights import build_insights
from paper2exp.core.paper_only.render import render_report
from paper2exp.core.paper_only.schema import (
    validate_applications,
    validate_facts,
    validate_insights,
)
from paper2exp.core.utils import write_text
from paper2exp.core.llm.base import LLMClient


def run_paper_only(
    run_dir: Path,
    *,
    lang: str = "ja",
    max_applications: int = 6,
    no_llm: bool = False,
    llm: str = "none",
    llm_model: str = "gemini-2.5-flash",
    llm_client: Optional[LLMClient] = None,
) -> dict:
    out_dir = run_dir / "paper_only"
    out_dir.mkdir(parents=True, exist_ok=True)

    facts = build_facts(run_dir)
    insights = build_insights(run_dir)
    applications = build_applications(
        run_dir,
        insights.get("signals", []),
        max_items=max_applications,
        lang=lang,
        no_llm=no_llm,
        llm=llm,
        llm_model=llm_model,
        llm_client=llm_client,
    )

    ok, err = validate_facts(facts)
    if not ok:
        facts = {**facts, "facts": {}, "evidence": []}

    ok, err = validate_insights(insights)
    if not ok:
        insights = {**insights, "signals": [], "blockers": [], "next_actions": []}

    apps_payload = {key: value for key, value in applications.items() if key != "_llm_used"}
    ok, err = validate_applications(apps_payload)
    if not ok:
        applications = {**applications, "applications": []}
        apps_payload = {
            "run_id": applications.get("run_id", ""),
            "paper_id": applications.get("paper_id", ""),
            "applications": [],
        }

    (out_dir / "facts.json").write_text(
        _safe_json(facts), encoding="utf-8"
    )
    (out_dir / "insights.json").write_text(
        _safe_json(insights), encoding="utf-8"
    )
    (out_dir / "applications.json").write_text(
        _safe_json(apps_payload), encoding="utf-8"
    )

    report = render_report(facts, insights, applications, lang=lang)
    write_text(out_dir / "report.md", report)
    return {
        "facts": facts,
        "insights": insights,
        "applications": applications,
        "report_path": str(out_dir / "report.md"),
    }


def _safe_json(data: dict) -> str:
    import json

    return json.dumps(data, indent=2, ensure_ascii=False)
