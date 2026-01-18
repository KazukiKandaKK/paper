from __future__ import annotations

from pathlib import Path

from paper2exp.core.paper_only.evidence import EvidenceBuilder
from paper2exp.core.paper_only.repo_extract import extract_repo_facts
from paper2exp.core.paper_only.repo_index import index_repo


def build_facts(run_dir: Path) -> dict:
    evidence = EvidenceBuilder()
    code_dir = run_dir / "code"
    facts = {
        "entrypoints": [],
        "dependencies": [],
        "repro_steps": [],
        "eval_harness": [],
        "config_surface": [],
    }
    if code_dir.exists():
        files = index_repo(code_dir)
        repo_facts, _, builder = extract_repo_facts(code_dir, files)
        facts = {
            "entrypoints": repo_facts.get("entrypoints", []),
            "dependencies": repo_facts.get("dependencies", []),
            "repro_steps": repo_facts.get("repro_steps", []),
            "eval_harness": repo_facts.get("eval_harness", []),
            "config_surface": repo_facts.get("config_surface", []),
        }
        evidence = builder

    metadata_path = run_dir / "paper" / "metadata.json"
    if metadata_path.exists():
        import json

        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
        if meta.get("id"):
            evidence.add("metadata", "paper/metadata.json:id", f"id={meta.get('id')}")
        links = meta.get("links")
        if isinstance(links, dict):
            for key, value in links.items():
                if value:
                    evidence.add("metadata", f"paper/metadata.json:links:{key}", f"{key}={value}")

    return {
        "run_id": run_dir.name,
        "paper_id": _read_paper_id(run_dir),
        "paper_repo": str(code_dir) if code_dir.exists() else None,
        "facts": facts,
        "evidence": evidence.items(),
    }


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
