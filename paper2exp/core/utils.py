import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


def utc_timestamp() -> str:
    override = os.getenv("PAPER2EXP_NOW")
    if override:
        return override
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_slug(value: str, max_len: int = 80) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:max_len] or "paper"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def append_jsonl(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data) + "\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def now_unix() -> float:
    return time.time()


def truncate_text(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def flatten(items: Iterable[Iterable[str]]) -> list[str]:
    return [item for group in items for item in group]


def is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y"}
