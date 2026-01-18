from __future__ import annotations

from pathlib import Path
from typing import Optional

from paper2exp.core.run.runner import Runner


def clone_repo(repo_url: Optional[str], dest_dir: Path, runner: Runner) -> bool:
    if not repo_url:
        return False
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists() and any(dest_dir.iterdir()):
        return True
    cmd = ["git", "clone", repo_url, str(dest_dir)]
    result = runner.run(cmd, cwd=dest_dir.parent)
    return result.get("exit_code") == 0
