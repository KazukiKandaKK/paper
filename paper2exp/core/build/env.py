from __future__ import annotations

import sys
from pathlib import Path

from paper2exp.core.run.runner import Runner
from paper2exp.core.utils import write_text


def venv_python(venv_dir: Path) -> Path:
    return venv_dir / "bin" / "python"


def build_env(
    run_dir: Path,
    code_dir: Path,
    runner: Runner,
    no_exec: bool,
    allow_package_install: bool = False,
) -> Path:
    venv_dir = run_dir / ".venv"
    if no_exec:
        env_freeze_path = run_dir / "repro" / "env_freeze.txt"
        write_text(env_freeze_path, "python --version (skipped)\npip freeze (skipped)\n")
        return venv_dir
    if not venv_dir.exists():
        runner.run([sys.executable, "-m", "venv", str(venv_dir)], cwd=run_dir)
    py_path = venv_python(venv_dir)
    if not py_path.exists():
        py_path = Path(sys.executable)

    requirements = code_dir / "requirements.txt"
    pyproject = code_dir / "pyproject.toml"
    if allow_package_install:
        if requirements.exists():
            runner.run(
                [str(py_path), "-m", "pip", "install", "-r", str(requirements)],
                cwd=code_dir,
            )
        elif pyproject.exists():
            runner.run([str(py_path), "-m", "pip", "install", "-e", "."], cwd=code_dir)
        else:
            runner.run([str(py_path), "-m", "pip", "install", "-U", "pip"], cwd=run_dir)

    env_freeze_path = run_dir / "repro" / "env_freeze.txt"
    if no_exec:
        write_text(env_freeze_path, "python --version (skipped)\npip freeze (skipped)\n")
        return venv_dir
    version_res = runner.run([str(py_path), "--version"], cwd=run_dir)
    freeze_res = runner.run([str(py_path), "-m", "pip", "freeze"], cwd=run_dir)
    content = "python --version\n"
    content += (version_res.get("stdout_tail") or "") + "\n"
    content += "pip freeze\n"
    content += (freeze_res.get("stdout_tail") or "") + "\n"
    write_text(env_freeze_path, content)
    return venv_dir
