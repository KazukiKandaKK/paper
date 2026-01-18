from __future__ import annotations

from typing import Iterable

from paper2exp.core.utils import truncate_text


def render_insights_md(insights: dict, lang: str = "ja", *, llm_used: bool = False) -> str:
    if lang not in {"ja", "en"}:
        lang = "ja"
    if lang == "en":
        return _render_en(insights, llm_used=llm_used)
    return _render_ja(insights, llm_used=llm_used)


def _render_ja(insights: dict, *, llm_used: bool) -> str:
    maturity = insights.get("maturity", {})
    lines = ["# Insights", ""]
    lines.append("## 概要")
    lines.append(f"- 成熟度: {maturity.get('level')}")
    lines.append(f"- 理由: {maturity.get('reason')}")
    lines.append("")
    lines.append("## 観測された事実")
    for signal in insights.get("signals", []):
        quote = truncate_text(signal.get("quote", ""), max_chars=160)
        lines.append(f"- [{signal.get('id')}] {quote}")
    lines.append("")
    lines.append("## 詰まりどころ")
    blockers = insights.get("blockers", [])
    if not blockers:
        lines.append("- なし")
    else:
        for blocker in blockers:
            lines.append(
                f"- {blocker.get('kind')} ({blocker.get('severity')}): {blocker.get('description')}"
            )
    lines.append("")
    lines.append("## 次の一手")
    next_actions = insights.get("next_actions", [])
    if not next_actions:
        lines.append("- (LLM未使用または提案なし)")
    else:
        for action in next_actions:
            lines.append(f"- {action.get('title')}: {action.get('why')}")
    lines.append("")
    lines.append("## 応用アイデア（提案/inference）")
    applications = insights.get("applications", [])
    if not applications:
        lines.append("- (なし)")
    else:
        for app in applications:
            lines.append(f"- {app.get('domain')}: {app.get('proposal')}")
    lines.append("")
    lines.append("## 監査ファイル")
    lines.append("- insights/insights.json")
    lines.append("- insights/insights.md")
    if llm_used:
        lines.append("- insights/llm_prompt.txt")
        lines.append("- insights/llm_schema.json")
        lines.append("- insights/llm_response.json")
        lines.append("- insights/llm_decision.md")
    return "\n".join(lines).strip() + "\n"


def _render_en(insights: dict, *, llm_used: bool) -> str:
    maturity = insights.get("maturity", {})
    lines = ["# Insights", ""]
    lines.append("## Summary")
    lines.append(f"- Maturity: {maturity.get('level')}")
    lines.append(f"- Reason: {maturity.get('reason')}")
    lines.append("")
    lines.append("## Observed facts")
    for signal in insights.get("signals", []):
        quote = truncate_text(signal.get("quote", ""), max_chars=160)
        lines.append(f"- [{signal.get('id')}] {quote}")
    lines.append("")
    lines.append("## Blockers")
    blockers = insights.get("blockers", [])
    if not blockers:
        lines.append("- None")
    else:
        for blocker in blockers:
            lines.append(
                f"- {blocker.get('kind')} ({blocker.get('severity')}): {blocker.get('description')}"
            )
    lines.append("")
    lines.append("## Next actions")
    next_actions = insights.get("next_actions", [])
    if not next_actions:
        lines.append("- (LLM not used or no proposals)")
    else:
        for action in next_actions:
            lines.append(f"- {action.get('title')}: {action.get('why')}")
    lines.append("")
    lines.append("## Applications (inference)")
    applications = insights.get("applications", [])
    if not applications:
        lines.append("- (None)")
    else:
        for app in applications:
            lines.append(f"- {app.get('domain')}: {app.get('proposal')}")
    lines.append("")
    lines.append("## Audit files")
    lines.append("- insights/insights.json")
    lines.append("- insights/insights.md")
    if llm_used:
        lines.append("- insights/llm_prompt.txt")
        lines.append("- insights/llm_schema.json")
        lines.append("- insights/llm_response.json")
        lines.append("- insights/llm_decision.md")
    return "\n".join(lines).strip() + "\n"
