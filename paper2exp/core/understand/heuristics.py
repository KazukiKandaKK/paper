from __future__ import annotations

import re
from typing import Iterable

GITHUB_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def extract_github_links(text: str) -> list[str]:
    candidates = []
    for match in GITHUB_RE.finditer(text or ""):
        org, repo = match.group(1), match.group(2)
        url = f"https://github.com/{org}/{repo}"
        if url not in candidates:
            candidates.append(url)
    return candidates


def pick_primary_repo(candidates: Iterable[str]) -> str | None:
    for url in candidates:
        if "github.com" in url:
            return url
    return None
