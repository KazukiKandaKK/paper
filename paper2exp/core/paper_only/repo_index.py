from __future__ import annotations

from pathlib import Path


def index_repo(base_dir: Path, *, max_bytes: int = 500_000) -> list[Path]:
    candidates: list[Path] = []
    for path in base_dir.rglob("*"):
        if path.is_dir():
            continue
        if _is_ignored(path, base_dir):
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
        except OSError:
            continue
        if _is_relevant(path, base_dir):
            candidates.append(path)
    return candidates


def _is_ignored(path: Path, base_dir: Path) -> bool:
    ignore_dirs = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache"}
    rel = path.relative_to(base_dir)
    if any(part in ignore_dirs for part in rel.parts):
        return True
    if path.name.startswith("."):
        return True
    return False


def _is_relevant(path: Path, base_dir: Path) -> bool:
    name = path.name.lower()
    rel = path.relative_to(base_dir)
    if name.startswith("readme"):
        return True
    if name in {"pyproject.toml", "environment.yml", "dockerfile", "makefile"}:
        return True
    if name.startswith("requirements") and name.endswith(".txt"):
        return True
    if rel.parts and rel.parts[0] in {"docs", "scripts", "src", "tests", "configs", "config"}:
        return True
    if path.suffix in {".md", ".py", ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini"}:
        return True
    return False
