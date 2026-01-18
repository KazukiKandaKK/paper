from __future__ import annotations

from paper2exp.core.utils import truncate_text


def render_report(
    facts: dict,
    insights: dict,
    applications: dict,
    lang: str = "ja",
) -> str:
    if lang not in {"ja", "en"}:
        lang = "ja"
    if lang == "en":
        return _render_en(facts, insights, applications)
    return _render_ja(facts, insights, applications)


def _render_ja(facts: dict, insights: dict, applications: dict) -> str:
    lines = ["# Paper-only Report", ""]
    lines.append("## 概要")
    maturity = insights.get("maturity", {})
    lines.append(f"- maturity: {maturity.get('level')}")
    lines.append(f"- reason: {maturity.get('reason')}")
    lines.append("")
    lines.append("## 事実（facts）")
    for key in ["entrypoints", "dependencies", "repro_steps", "eval_harness", "config_surface"]:
        items = facts.get("facts", {}).get(key, [])
        lines.append(f"- {key}: {', '.join(items) if items else '(なし)'}")
    lines.append("")
    lines.append("## 詰まり（blockers）")
    blockers = insights.get("blockers", [])
    if not blockers:
        lines.append("- なし")
    else:
        for b in blockers:
            lines.append(f"- {b.get('kind')}: {b.get('description')}")
    lines.append("")
    lines.append("## 次の一手（next_actions）")
    next_actions = insights.get("next_actions", [])
    if not next_actions:
        lines.append("- なし")
    else:
        for act in next_actions:
            lines.append(f"- {act.get('title')}: {truncate_text(act.get('why',''), 160)}")
    lines.append("")
    lines.append("## 応用案（inference）")
    apps = applications.get("applications", [])
    if not apps:
        lines.append("- (なし)")
    else:
        for app in apps:
            lines.append(f"- {app.get('domain')}: {truncate_text(app.get('proposal',''), 160)}")
    lines.append("")
    lines.append("## 監査ファイル")
    lines.append("- paper_only/facts.json")
    lines.append("- paper_only/insights.json")
    lines.append("- paper_only/applications.json")
    lines.append("- paper_only/report.md")
    if applications.get("_llm_used"):
        lines.append("- paper_only/llm_prompt.txt")
        lines.append("- paper_only/llm_schema.json")
        lines.append("- paper_only/llm_response.json")
        lines.append("- paper_only/llm_decision.md")
    return "\n".join(lines).strip() + "\n"


def _render_en(facts: dict, insights: dict, applications: dict) -> str:
    lines = ["# Paper-only Report", ""]
    lines.append("## Summary")
    maturity = insights.get("maturity", {})
    lines.append(f"- maturity: {maturity.get('level')}")
    lines.append(f"- reason: {maturity.get('reason')}")
    lines.append("")
    lines.append("## Facts")
    for key in ["entrypoints", "dependencies", "repro_steps", "eval_harness", "config_surface"]:
        items = facts.get("facts", {}).get(key, [])
        lines.append(f"- {key}: {', '.join(items) if items else '(none)'}")
    lines.append("")
    lines.append("## Blockers")
    blockers = insights.get("blockers", [])
    if not blockers:
        lines.append("- none")
    else:
        for b in blockers:
            lines.append(f"- {b.get('kind')}: {b.get('description')}")
    lines.append("")
    lines.append("## Next actions")
    next_actions = insights.get("next_actions", [])
    if not next_actions:
        lines.append("- none")
    else:
        for act in next_actions:
            lines.append(f"- {act.get('title')}: {truncate_text(act.get('why',''), 160)}")
    lines.append("")
    lines.append("## Applications (inference)")
    apps = applications.get("applications", [])
    if not apps:
        lines.append("- (none)")
    else:
        for app in apps:
            lines.append(f"- {app.get('domain')}: {truncate_text(app.get('proposal',''), 160)}")
    lines.append("")
    lines.append("## Audit files")
    lines.append("- paper_only/facts.json")
    lines.append("- paper_only/insights.json")
    lines.append("- paper_only/applications.json")
    lines.append("- paper_only/report.md")
    if applications.get("_llm_used"):
        lines.append("- paper_only/llm_prompt.txt")
        lines.append("- paper_only/llm_schema.json")
        lines.append("- paper_only/llm_response.json")
        lines.append("- paper_only/llm_decision.md")
    return "\n".join(lines).strip() + "\n"
