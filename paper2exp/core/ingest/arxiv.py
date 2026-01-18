from __future__ import annotations

import re
from typing import Optional
from xml.etree import ElementTree

import requests

ARXIV_ID_RE = re.compile(r"(?P<id>\d{4}\.\d{4,5})(v\d+)?")


def parse_arxiv_id(paper_ref: str) -> Optional[str]:
    match = ARXIV_ID_RE.search(paper_ref)
    if not match:
        return None
    return match.group("id")


def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return {
            "id": f"arxiv:{arxiv_id}",
            "title": arxiv_id,
            "summary": "",
            "links": {},
        }
    title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
    summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
    links = {}
    for link in entry.findall("atom:link", ns):
        rel = link.attrib.get("rel")
        href = link.attrib.get("href")
        ltype = link.attrib.get("type")
        if rel == "alternate" and href:
            links["arxiv"] = href
        if ltype == "application/pdf" and href:
            links["pdf"] = href
    if "arxiv" not in links:
        links["arxiv"] = f"https://arxiv.org/abs/{arxiv_id}"
    if "pdf" not in links:
        links["pdf"] = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return {
        "id": f"arxiv:{arxiv_id}",
        "title": title or arxiv_id,
        "summary": summary,
        "links": links,
    }


def download_pdf(pdf_url: str, dest_path) -> bool:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        return True
    resp = requests.get(pdf_url, timeout=30)
    if resp.status_code != 200:
        return False
    dest_path.write_bytes(resp.content)
    return True
