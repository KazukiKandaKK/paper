from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re

from paper2exp.core.run.runner import Runner


@dataclass
class EnsurePytestResult:
    required: bool
    available: bool
    install_attempted: bool
    install_ok: bool | None
    reason: str


def ensure_pytest(
    python_path: Path,
    runner: Runner,
    *,
    allow_network: bool,
    allow_package_install: bool,
) -> EnsurePytestResult:
    required = True
    install_attempted = False
    install_ok: bool | None = None

    check = runner.run(
        [str(python_path), "-c", "import pytest; print(pytest.__version__)"],
        cwd=runner.logs_dir.parent,
    )
    if check.get("exit_code") == 0:
        return EnsurePytestResult(
            required=required,
            available=True,
            install_attempted=False,
            install_ok=None,
            reason="pytest already available",
        )

    reason = "pytest import failed"

    if allow_package_install and allow_network:
        install_attempted = True
        install = runner.run(
            [str(python_path), "-m", "pip", "install", "-U", "pytest"],
            cwd=runner.logs_dir.parent,
        )
        if install.get("exit_code") == 0:
            check = runner.run(
                [str(python_path), "-c", "import pytest; print(pytest.__version__)"],
                cwd=runner.logs_dir.parent,
            )
            if check.get("exit_code") == 0:
                return EnsurePytestResult(
                    required=required,
                    available=True,
                    install_attempted=True,
                    install_ok=True,
                    reason="pytest installed via pip",
                )
            install_ok = False
            reason = "pytest install reported success but import failed"
        else:
            install_ok = False
            reason = _classify_pip_failure(install.get("stderr_tail", ""))

    wheelhouse = os.getenv("PAPER2EXP_WHEELHOUSE")
    if not (install_ok is True) and allow_package_install and wheelhouse:
        install_attempted = True
        install = runner.run(
            [
                str(python_path),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                wheelhouse,
                "pytest",
            ],
            cwd=runner.logs_dir.parent,
        )
        if install.get("exit_code") == 0:
            check = runner.run(
                [str(python_path), "-c", "import pytest; print(pytest.__version__)"],
                cwd=runner.logs_dir.parent,
            )
            if check.get("exit_code") == 0:
                return EnsurePytestResult(
                    required=required,
                    available=True,
                    install_attempted=True,
                    install_ok=True,
                    reason="pytest installed from wheelhouse",
                )
            install_ok = False
            reason = "wheelhouse install succeeded but import failed"
        else:
            install_ok = False
            reason = _classify_pip_failure(install.get("stderr_tail", ""))

    return EnsurePytestResult(
        required=required,
        available=False,
        install_attempted=install_attempted,
        install_ok=install_ok,
        reason=reason,
    )


def _classify_pip_failure(stderr: str) -> str:
    text = (stderr or "").lower()
    if "nodename nor servname" in text or "could not resolve host" in text:
        return "pip install failed: network_dns"
    if "timed out" in text or "timeout" in text:
        return "pip install failed: timeout"
    if "proxy" in text:
        return "pip install failed: proxy"
    if "permission denied" in text or "not writable" in text:
        return "pip install failed: permission"
    if "no matching distribution found" in text:
        return "pip install failed: no matching distribution"
    return "pip install failed"
