from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional

import requests

from paper2exp.core.ingest import arxiv as arxiv_ingest
from paper2exp.core.ingest import hf as hf_ingest
from collections import OrderedDict



@dataclass
class PaperMetadata:
    id: str
    title: str
    summary: str
    links: dict
    arxiv_id: Optional[str] = None
    repo_candidates: list[str] = None


def ingest_paper(
    paper_ref: str,
    paper_dir: Path,
    allow_metadata_fetch: bool = True,
    download_pdf: bool = False,
) -> PaperMetadata:
    paper_dir.mkdir(parents=True, exist_ok=True)
    arxiv_id = arxiv_ingest.parse_arxiv_id(paper_ref)
    metadata: dict
    if not allow_metadata_fetch:
        metadata = {
            "id": f"arxiv:{arxiv_id}" if arxiv_id else paper_ref,
            "title": "",
            "summary": "",
            "links": {
                "arxiv": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
                "pdf": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                "hf": None,
            },
        }
    else:
        if "huggingface.co/papers" in paper_ref:
            metadata = hf_ingest.fetch_hf_metadata(paper_ref)
            if metadata.get("arxiv_id"):
                arxiv_id = metadata["arxiv_id"]
        elif arxiv_id:
            metadata = arxiv_ingest.fetch_arxiv_metadata(arxiv_id)
        else:
            metadata = {
                "id": paper_ref,
                "title": paper_ref,
                "summary": "",
                "links": {"url": paper_ref},
            }

    paper_id = metadata.get("id") or (f"arxiv:{arxiv_id}" if arxiv_id else paper_ref)
    links = metadata.get("links", {})
    summary = metadata.get("summary", "")
    title = metadata.get("title", paper_id)

    pdf_url = links.get("pdf") if isinstance(links, dict) else None
    pdf_path = paper_dir / "paper.pdf"
    pdf_ok = False
    if pdf_url and download_pdf:
        try:
            pdf_ok = arxiv_ingest.download_pdf(pdf_url, pdf_path)
        except requests.RequestException:
            pdf_ok = False
    metadata_out = OrderedDict()
    metadata_out["id"] = paper_id
    metadata_out["title"] = title
    metadata_out["summary"] = summary
    metadata_out["links"] = links
    metadata_out["pdf_downloaded"] = pdf_ok
    if arxiv_id:
        metadata_out["arxiv_id"] = arxiv_id
    (paper_dir / "metadata.json").write_text(
        json.dumps(metadata_out, indent=2), encoding="utf-8"
    )

    return PaperMetadata(
        id=paper_id,
        title=title,
        summary=summary,
        links=links,
        arxiv_id=arxiv_id,
        repo_candidates=[],
    )
