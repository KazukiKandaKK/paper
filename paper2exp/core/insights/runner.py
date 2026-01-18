from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from paper2exp.core.insights.classify_blockers import classify_blockers
from paper2exp.core.insights.collect_signals import collect_signals
from paper2exp.core.insights.maturity import compute_maturity
from paper2exp.core.insights.prompts import INSIGHTS_PROMPT_TEMPLATE, SYSTEM_PROMPT
from paper2exp.core.insights.render import render_insights_md
from paper2exp.core.insights.schema import (
    INSIGHTS_LLM_SCHEMA,
    INSIGHTS_SCHEMA,
    validate_insights,
    validate_insights_llm,
)
from paper2exp.core.llm.base import LLMClient
from paper2exp.core.llm.manager import get_llm_client
from paper2exp.core.models import ExperimentSpec
from paper2exp.core.utils import truncate_text, write_text


def run_insights(
    run_dir: Path,
    spec: ExperimentSpec,
    *,
    llm: str,
    llm_model: str,
    insights_lang: str = "ja",
    insights_max_applications: int = 6,
    insights_no_llm: bool = False,
    llm_client: Optional[LLMClient] = None,
) -> dict:
    insights_dir = run_dir / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)

    signals = collect_signals(run_dir)
    blockers = classify_blockers(signals)
    repo_cloned = (run_dir / "code" / ".git").exists()
    paper_to_code_generated = (run_dir / "paper_to_code" / "plan.md").exists()
    maturity = compute_maturity(run_dir, repo_cloned, paper_to_code_generated)

    insights = {
        "run_id": run_dir.name,
        "paper_id": spec.paper.id,
        "maturity": {"level": maturity.level, "reason": maturity.reason},
        "signals": signals,
        "blockers": blockers,
        "next_actions": [],
        "applications": [],
    }

    llm_used = llm == "gemini" and not insights_no_llm
    decision_lines = []
    if llm_used:
        if llm_client is None:
            llm_client = get_llm_client(llm)
        prompt = "\n\n".join(
            [
                SYSTEM_PROMPT,
                INSIGHTS_PROMPT_TEMPLATE.format(
                    language=insights_lang,
                    max_applications=insights_max_applications,
                    run_id=run_dir.name,
                    paper_id=spec.paper.id,
                    maturity_level=maturity.level,
                    maturity_reason=maturity.reason,
                    blockers_json=json.dumps(blockers, ensure_ascii=False),
                    signals_json=json.dumps(signals, ensure_ascii=False),
                ),
            ]
        )
        write_text(insights_dir / "llm_prompt.txt", prompt)
        (insights_dir / "llm_schema.json").write_text(
            json.dumps(INSIGHTS_LLM_SCHEMA, indent=2), encoding="utf-8"
        )
        response = llm_client.generate_structured(
            prompt, INSIGHTS_LLM_SCHEMA, model=llm_model, temperature=0.0
        )
        (insights_dir / "llm_response.json").write_text(
            json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        ok, err = validate_insights_llm(response)
        if not ok:
            decision_lines.append(f"- rejected: schema invalid: {err}")
        elif _contains_secret(response):
            decision_lines.append("- rejected: secret-like content detected")
        else:
            next_actions = _sanitize_next_actions(
                response.get("next_actions", []),
                signals,
            )
            applications = _sanitize_applications(
                response.get("applications", []),
                signals,
                max_items=insights_max_applications,
            )
            insights["next_actions"] = next_actions
            insights["applications"] = applications
            decision_lines.append(f"- accepted next_actions: {len(next_actions)}")
            decision_lines.append(f"- accepted applications: {len(applications)}")
        write_text(insights_dir / "llm_decision.md", "\n".join(decision_lines) or "no decisions")

    ok, err = validate_insights(insights)
    if not ok:
        decision_lines.append(f"- final insights invalid: {err}")
        insights["next_actions"] = []
        insights["applications"] = []
    (insights_dir / "insights.json").write_text(
        json.dumps(insights, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md = render_insights_md(insights, lang=insights_lang, llm_used=llm_used)
    write_text(insights_dir / "insights.md", md)
    return insights


def _contains_secret(payload: dict) -> bool:
    text = json.dumps(payload, ensure_ascii=False)
    patterns = [
        r"AIza[0-9A-Za-z\-_]{10,}",
        r"sk-[0-9A-Za-z]{8,}",
        r"AKIA[0-9A-Z]{16}",
        r"BEGIN PRIVATE KEY",
        r"GOOGLE_API_KEY",
    ]
    return any(re.search(pat, text) for pat in patterns)


def _sanitize_next_actions(next_actions: list[dict], signals: list[dict]) -> list[dict]:
    valid_signal_ids = {s.get("id") for s in signals}
    signal_quotes = [s.get("quote", "") for s in signals]
    sanitized: list[dict] = []
    for action in next_actions:
        if not isinstance(action, dict):
            continue
        signal_ids = [sid for sid in action.get("signal_ids", []) if sid in valid_signal_ids]
        if not signal_ids:
            continue
        action["signal_ids"] = signal_ids
        text_blob = f"{action.get('title','')} {action.get('why','')}"
        urls = re.findall(r"https?://\\S+", text_blob)
        if urls and not _quotes_contain_all(signal_quotes, urls):
            action["needs_approval"] = True
            if action.get("risk") == "low":
                action["risk"] = "medium"
        if _contains_command_hint(text_blob) and not _quotes_contain_any(signal_quotes, ["pip", "pytest", "git", "python"]):
            action["needs_approval"] = True
            if action.get("risk") == "low":
                action["risk"] = "medium"
        sanitized.append(action)
    return sanitized


def _sanitize_applications(applications: list[dict], signals: list[dict], max_items: int) -> list[dict]:
    valid_signal_ids = {s.get("id") for s in signals}
    sanitized: list[dict] = []
    for app in applications:
        if not isinstance(app, dict):
            continue
        signal_ids = [sid for sid in app.get("signal_ids", []) if sid in valid_signal_ids]
        if not signal_ids:
            continue
        app["signal_ids"] = signal_ids
        app["basis"] = "inference"
        sanitized.append(app)
        if len(sanitized) >= max_items:
            break
    return sanitized


def _contains_command_hint(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ["pip install", "pytest", "git clone", "python -m", "make test"])


def _quotes_contain_all(quotes: list[str], tokens: list[str]) -> bool:
    corpus = " ".join(quotes)
    return all(token in corpus for token in tokens)


def _quotes_contain_any(quotes: list[str], tokens: list[str]) -> bool:
    corpus = " ".join(quotes)
    return any(token in corpus for token in tokens)
