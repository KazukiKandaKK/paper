from __future__ import annotations

from pathlib import Path
from typing import Optional

from paper2exp.core.run.runner import Runner
from paper2exp.core.utils import is_truthy_env


def clone_repo(repo_url: Optional[str], dest_dir: Path, runner: Runner) -> bool:
    if not repo_url:
        return False
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists() and any(dest_dir.iterdir()):
        return True
    repo_url = _maybe_use_ssh(repo_url)
    cmd = ["git", "clone"]
    shallow = is_truthy_env("PAPER2EXP_GIT_SHALLOW")
    if shallow:
        cmd += ["--depth", "1", "--filter=blob:none", "--single-branch"]
    cmd += [repo_url, str(dest_dir)]
    if shallow or is_truthy_env("PAPER2EXP_GIT_LFS_SKIP"):
        cmd = ["env", "GIT_LFS_SKIP_SMUDGE=1", "GIT_TERMINAL_PROMPT=0"] + cmd
    else:
        cmd = ["env", "GIT_TERMINAL_PROMPT=0"] + cmd
    result = runner.run(cmd, cwd=dest_dir.parent)
    return result.get("exit_code") == 0


def _maybe_use_ssh(repo_url: str) -> str:
    if not is_truthy_env("PAPER2EXP_GIT_USE_SSH"):
        return repo_url
    if repo_url.startswith("https://github.com/"):
        path = repo_url.replace("https://github.com/", "")
        if not path.endswith(".git"):
            path += ".git"
        return f"git@github.com:{path}"
    return repo_url
