from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from paper2exp.core.utils import sha1_text


def error_signature(text: str) -> str:
    return sha1_text(text.strip()[-500:])


def record_failure(run_dir: Path, stderr_tail: str, context: dict) -> None:
    memory_dir = run_dir / "_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    signature = error_signature(stderr_tail)
    entry = {
        "error_signature": signature,
        "fix_applied": None,
        "success": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context,
    }
    path = memory_dir / f"{signature}.json"
    path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
