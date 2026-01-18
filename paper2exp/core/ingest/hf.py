from __future__ import annotations

import re
from typing import Optional

import requests

ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5})(v\d+)?\b")


def fetch_hf_metadata(hf_url: str) -> dict:
    resp = requests.get(hf_url, timeout=20)
    resp.raise_for_status()
    text = resp.text
    arxiv_id = None
    match = ARXIV_ID_RE.search(text)
    if match:
        arxiv_id = match.group(1)
    title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    title = ""
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
    return {
        "id": f"hf:{hf_url.split('/')[-1]}",
        "title": title or hf_url,
        "summary": "",
        "links": {
            "hf": hf_url,
            "arxiv": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
            "pdf": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
        },
        "arxiv_id": arxiv_id,
    }
