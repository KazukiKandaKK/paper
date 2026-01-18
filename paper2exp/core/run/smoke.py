from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Sequence

from paper2exp.core.utils import write_text


def _has_make_test(makefile: Path) -> bool:
    if not makefile.exists():
        return False
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if re.match(r"^test\s*:", line):
            return True
    return False


def _has_tests(code_dir: Path) -> bool:
    if (code_dir / "tests").exists():
        return True
    for path in code_dir.rglob("test_*.py"):
        return True
    return False


def select_smoke_command(code_dir: Path, venv_python: Path) -> Sequence[str]:
    py_cmd = venv_python if venv_python.exists() else Path("python")
    if _has_make_test(code_dir / "Makefile"):
        return ["make", "test"]
    if _has_tests(code_dir):
        return [str(py_cmd), "-m", "pytest", "-q"]
    return [str(py_cmd), "-c", "print('smoke ok')"]


def write_run_script(path: Path, commands: list[list[str]]) -> None:
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    for cmd in commands:
        quoted = " ".join(_shell_quote(token) for token in cmd)
        lines.append(quoted)
    lines.append("")
    write_text(path, "\n".join(lines))
    path.chmod(0o755)


def _shell_quote(token: str) -> str:
    if token == "":
        return "''"
    if (
        '"' not in token
        and "$" not in token
        and "`" not in token
        and "\\" not in token
        and any(ch in token for ch in " \t\n'")
    ):
        return f"\"{token}\""
    return shlex.quote(token)
