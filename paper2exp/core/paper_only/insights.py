from __future__ import annotations

from pathlib import Path

from paper2exp.core.insights.classify_blockers import classify_blockers
from paper2exp.core.insights.maturity import compute_maturity
from paper2exp.core.paper_only.collect import collect_signals_for_insights


def build_insights(run_dir: Path) -> dict:
    signals = collect_signals_for_insights(run_dir)
    blockers = classify_blockers(signals)
    repo_cloned = (run_dir / "code" / ".git").exists()
    paper_to_code_generated = (run_dir / "paper_to_code" / "plan.md").exists()
    maturity = compute_maturity(run_dir, repo_cloned, paper_to_code_generated)
    paper_id = _read_paper_id(run_dir)

    next_actions = _next_actions_from_blockers(blockers)

    return {
        "run_id": run_dir.name,
        "paper_id": paper_id,
        "maturity": {"level": maturity.level, "reason": maturity.reason},
        "signals": signals,
        "blockers": blockers,
        "next_actions": next_actions,
    }


def _next_actions_from_blockers(blockers: list[dict]) -> list[dict]:
    actions: list[dict] = []
    for blocker in blockers:
        kind = blocker.get("kind")
        signal_ids = blocker.get("signal_ids", [])
        if kind == "missing_dependency":
            actions.append(
                {
                    "title": "pytestを導入して再実行",
                    "why": "pytestが不足しており、テストが失敗しています。",
                    "requires": {
                        "allow_network": True,
                        "allow_package_install": True,
                        "allow_write_repo": False,
                        "credentials_needed": False,
                    },
                    "risk": "medium",
                    "basis": "run_log",
                    "signal_ids": signal_ids,
                    "needs_approval": True,
                }
            )
        elif kind == "auth":
            actions.append(
                {
                    "title": "GitHub認証の設定",
                    "why": "リポジトリへの認証が必要です。",
                    "requires": {
                        "allow_network": False,
                        "allow_package_install": False,
                        "allow_write_repo": False,
                        "credentials_needed": True,
                    },
                    "risk": "medium",
                    "basis": "repo_validation",
                    "signal_ids": signal_ids,
                    "needs_approval": True,
                }
            )
        elif kind == "network_dns":
            actions.append(
                {
                    "title": "ネットワーク/DNSの確認",
                    "why": "外部接続に失敗しています。",
                    "requires": {
                        "allow_network": False,
                        "allow_package_install": False,
                        "allow_write_repo": False,
                        "credentials_needed": False,
                    },
                    "risk": "low",
                    "basis": "run_log",
                    "signal_ids": signal_ids,
                    "needs_approval": False,
                }
            )
        elif kind == "repo_not_found":
            actions.append(
                {
                    "title": "公式リポジトリURLの再確認",
                    "why": "Repository not found が発生しています。",
                    "requires": {
                        "allow_network": False,
                        "allow_package_install": False,
                        "allow_write_repo": False,
                        "credentials_needed": False,
                    },
                    "risk": "low",
                    "basis": "repo_validation",
                    "signal_ids": signal_ids,
                    "needs_approval": False,
                }
            )

    return actions


def _read_paper_id(run_dir: Path) -> str:
    meta_path = run_dir / "paper" / "metadata.json"
    if not meta_path.exists():
        return ""
    import json

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return meta.get("id", "")
