from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from paper2exp.core.llm.base import LLMClient
from paper2exp.core.llm.manager import get_llm_client
from paper2exp.core.paper_only.prompts import APPLICATIONS_PROMPT_TEMPLATE, SYSTEM_PROMPT
from paper2exp.core.paper_only.schema import (
    APPLICATIONS_LLM_SCHEMA,
    validate_applications,
    validate_applications_llm,
)
from paper2exp.core.utils import write_text


def build_applications(
    run_dir: Path,
    signals: list[dict],
    *,
    max_items: int,
    lang: str,
    no_llm: bool,
    llm: str,
    llm_model: str,
    llm_client: Optional[LLMClient] = None,
) -> dict:
    paper_id = _read_paper_id(run_dir)
    bundle = {
        "run_id": run_dir.name,
        "paper_id": paper_id,
        "applications": [],
        "_llm_used": False,
    }
    decision_lines = []

    if no_llm or llm == "none":
        bundle["applications"] = _rule_based_applications(signals, max_items)
    else:
        bundle["_llm_used"] = True
        if llm_client is None:
            llm_client = get_llm_client(llm)
        prompt = "\n\n".join(
            [
                SYSTEM_PROMPT,
                APPLICATIONS_PROMPT_TEMPLATE.format(
                    language=lang,
                    max_items=max_items,
                    run_id=run_dir.name,
                    paper_id=paper_id,
                    signals_json=json.dumps(signals, ensure_ascii=False),
                ),
            ]
        )
        out_dir = run_dir / "paper_only"
        out_dir.mkdir(parents=True, exist_ok=True)
        write_text(out_dir / "llm_prompt.txt", prompt)
        (out_dir / "llm_schema.json").write_text(
            json.dumps(APPLICATIONS_LLM_SCHEMA, indent=2), encoding="utf-8"
        )
        response = llm_client.generate_structured(
            prompt, APPLICATIONS_LLM_SCHEMA, model=llm_model, temperature=0.0
        )
        (out_dir / "llm_response.json").write_text(
            json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        ok, err = validate_applications_llm(response)
        if not ok:
            decision_lines.append(f"- rejected: schema invalid: {err}")
        elif _contains_secret(response):
            decision_lines.append("- rejected: secret-like content detected")
        else:
            apps = _sanitize_applications(response.get("applications", []), signals, max_items)
            bundle["applications"] = apps
            decision_lines.append(f"- accepted applications: {len(apps)}")
        write_text(out_dir / "llm_decision.md", "\n".join(decision_lines) or "no decisions")

    payload = {key: value for key, value in bundle.items() if key != "_llm_used"}
    ok, err = validate_applications(payload)
    if not ok:
        bundle["applications"] = []
        decision_lines.append(f"- final applications invalid: {err}")
    return bundle


def _rule_based_applications(signals: list[dict], max_items: int) -> list[dict]:
    signal_ids = [s.get("id") for s in signals if s.get("id")]
    if not signal_ids:
        return []
    base_id = signal_ids[0]
    proposals = [
        {
            "domain": "reproducibility",
            "proposal": "再現手順を小さなタスクに分割して再利用する。",
            "why_it_fits": "runの観測情報があるため、手順分割の起点になる。",
            "prerequisites": ["再現ログ", "手順の整理"],
            "risk": "low",
            "basis": "inference",
            "signal_ids": [base_id],
        },
        {
            "domain": "evaluation",
            "proposal": "評価手順を共通テンプレ化し、別の実験に適用する。",
            "why_it_fits": "評価ログがあるため、共通化の土台になる。",
            "prerequisites": ["評価ログ", "共通テンプレ"],
            "risk": "medium",
            "basis": "inference",
            "signal_ids": [base_id],
        },
    ]
    return proposals[:max_items]


def _sanitize_applications(applications: list[dict], signals: list[dict], max_items: int) -> list[dict]:
    valid_ids = {s.get("id") for s in signals}
    sanitized = []
    for app in applications:
        if app.get("basis") != "inference":
            continue
        ids = [sid for sid in app.get("signal_ids", []) if sid in valid_ids]
        if not ids:
            continue
        app["signal_ids"] = ids
        sanitized.append(app)
        if len(sanitized) >= max_items:
            break
    return sanitized


def _contains_secret(payload: dict) -> bool:
    text = json.dumps(payload, ensure_ascii=False)
    patterns = [
        r"AIza[0-9A-Za-z\\-_]{10,}",
        r"sk-[0-9A-Za-z]{8,}",
        r"AKIA[0-9A-Z]{16}",
        r"BEGIN PRIVATE KEY",
        r"GOOGLE_API_KEY",
    ]
    return any(re.search(pat, text) for pat in patterns)


def _read_paper_id(run_dir: Path) -> str:
    meta_path = run_dir / "paper" / "metadata.json"
    if not meta_path.exists():
        return ""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return meta.get("id", "")
