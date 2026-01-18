from __future__ import annotations

from dataclasses import dataclass

from paper2exp.core.repo.discovery import RepoCandidate
from paper2exp.core.repo.validate import ValidationResult


@dataclass
class SelectionResult:
    selected_url: str | None
    reason: str
    fallback_reason: str | None = None


def select_repo(
    candidates: list[RepoCandidate],
    validation: list[ValidationResult],
    strategy: str,
) -> SelectionResult:
    status_map = {item.url: item.status for item in validation}
    ok_urls = {item.url for item in validation if item.status == "ok"}
    ordered = _order_candidates(candidates, strategy)

    for cand in ordered:
        if cand.url in ok_urls or cand.normalized_url in ok_urls:
            return SelectionResult(
                selected_url=cand.normalized_url,
                reason=f"selected {cand.normalized_url} via {strategy} (ok)",
            )
    if ok_urls:
        url = list(ok_urls)[0]
        return SelectionResult(selected_url=url, reason="selected first ok url")
    return SelectionResult(selected_url=None, reason="no reachable repo candidates")


def _order_candidates(candidates: list[RepoCandidate], strategy: str) -> list[RepoCandidate]:
    def priority_key(cand: RepoCandidate) -> tuple[int, int]:
        return (cand.priority_rank, 0)

    ordered = sorted(candidates, key=priority_key)
    if strategy == "prefer_paper_then_user":
        ordered = sorted(
            candidates,
            key=lambda c: (0 if c.source in {"paper_text", "pdf_text"} else 1, c.priority_rank),
        )
    elif strategy == "prefer_llm_last":
        ordered = sorted(
            candidates,
            key=lambda c: (1 if c.source == "llm" else 0, c.priority_rank),
        )
    return ordered
