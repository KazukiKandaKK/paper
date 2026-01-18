from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from paper2exp.core.llm.chunking import chunk_text

GITHUB_RE = re.compile(r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+[A-Za-z0-9_.-/]*")


@dataclass
class RepoEvidence:
    locator: str
    quote: str


@dataclass
class RepoCandidate:
    url: str
    normalized_url: str
    source: str
    priority_rank: int
    evidence: RepoEvidence | None = None


def normalize_github_url(url: str) -> str:
    url = url.strip()
    url = url.split("#")[0]
    url = url.split("?")[0]
    url = url.replace("http://", "https://")
    if url.endswith(".git"):
        url = url[:-4]
    if url.startswith("https://github.com/"):
        path = url.replace("https://github.com/", "")
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            return f"https://github.com/{parts[0]}/{parts[1]}"
    return url


def extract_candidates_from_text(text: str, source: str) -> list[RepoCandidate]:
    candidates: list[RepoCandidate] = []
    chunks = chunk_text(text)
    for chunk in chunks:
        for idx, line in enumerate(chunk.text.splitlines(), start=chunk.start_line):
            for match in GITHUB_RE.findall(line):
                normalized = normalize_github_url(match)
                candidates.append(
                    RepoCandidate(
                        url=match,
                        normalized_url=normalized,
                        source=source,
                        priority_rank=0,
                        evidence=RepoEvidence(
                            locator=f"chunk:{chunk.chunk_id} lines:{idx}-{idx}",
                            quote=line.strip(),
                        ),
                    )
                )
    return _dedupe_candidates(candidates)


def candidate_from_user(url: str) -> RepoCandidate:
    return RepoCandidate(
        url=url,
        normalized_url=normalize_github_url(url),
        source="user_input",
        priority_rank=0,
        evidence=RepoEvidence(locator="user_input", quote=url),
    )


def extract_candidates_from_llm(response: dict, paper_text: str) -> list[RepoCandidate]:
    if not isinstance(response, dict):
        return []
    evidence = response.get("evidence", [])
    evidence_map = {item.get("id"): item for item in evidence if isinstance(item, dict)}
    patches = response.get("patches", [])
    candidates: list[RepoCandidate] = []
    paper_lower = (paper_text or "").lower()
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        if patch.get("path") != "/repro/repo/url":
            continue
        url = patch.get("value")
        if not isinstance(url, str):
            continue
        evidence_ids = patch.get("evidence_ids", [])
        matched = False
        locator = "llm"
        quote = ""
        for eid in evidence_ids:
            item = evidence_map.get(eid)
            if not item:
                continue
            if item.get("source") not in {"paper_text", "pdf_text"}:
                continue
            q = item.get("quote", "")
            if url in q:
                matched = True
                locator = item.get("locator", "llm")
                quote = q
                break
        if not matched:
            continue
        if url.lower() not in paper_lower:
            continue
        candidates.append(
            RepoCandidate(
                url=url,
                normalized_url=normalize_github_url(url),
                source="llm",
                priority_rank=0,
                evidence=RepoEvidence(locator=locator, quote=quote),
            )
        )
    return _dedupe_candidates(candidates)


def _dedupe_candidates(candidates: Iterable[RepoCandidate]) -> list[RepoCandidate]:
    seen: set[str] = set()
    unique: list[RepoCandidate] = []
    for cand in candidates:
        key = cand.normalized_url
        if key in seen:
            continue
        seen.add(key)
        unique.append(cand)
    return unique
