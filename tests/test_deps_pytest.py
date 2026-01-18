from pathlib import Path
import os

from paper2exp.core.build.deps import ensure_pytest


class DummyRunner:
    def __init__(self, responses, logs_dir: Path) -> None:
        self.responses = list(responses)
        self.logs_dir = logs_dir
        self.results_path = logs_dir / "results.jsonl"
        self.no_exec = False

    def run(self, command, cwd, timeout_sec=None):
        if not self.responses:
            return {"exit_code": 1, "stderr_tail": "no response"}
        return self.responses.pop(0)


def test_ensure_pytest_already_available(tmp_path: Path):
    runner = DummyRunner([{"exit_code": 0, "stderr_tail": ""}], tmp_path / "logs")
    result = ensure_pytest(Path("python"), runner, allow_network=False, allow_package_install=False)
    assert result.available is True
    assert result.install_attempted is False


def test_ensure_pytest_missing_no_install(tmp_path: Path):
    runner = DummyRunner([{"exit_code": 1, "stderr_tail": "No module named pytest"}], tmp_path / "logs")
    result = ensure_pytest(Path("python"), runner, allow_network=False, allow_package_install=False)
    assert result.available is False
    assert result.install_attempted is False


def test_ensure_pytest_install_failure_dns(tmp_path: Path):
    runner = DummyRunner(
        [
            {"exit_code": 1, "stderr_tail": "No module named pytest"},
            {"exit_code": 1, "stderr_tail": "nodename nor servname provided"},
        ],
        tmp_path / "logs",
    )
    result = ensure_pytest(Path("python"), runner, allow_network=True, allow_package_install=True)
    assert result.available is False
    assert result.install_attempted is True
    assert result.install_ok is False
    assert "network_dns" in result.reason


def test_ensure_pytest_wheelhouse(tmp_path: Path, monkeypatch):
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    monkeypatch.setenv("PAPER2EXP_WHEELHOUSE", str(wheelhouse))
    runner = DummyRunner(
        [
            {"exit_code": 1, "stderr_tail": "No module named pytest"},
            {"exit_code": 0, "stderr_tail": ""},
            {"exit_code": 0, "stderr_tail": ""},
        ],
        tmp_path / "logs",
    )
    result = ensure_pytest(Path("python"), runner, allow_network=False, allow_package_install=True)
    assert result.available is True
    assert result.install_attempted is True
    assert result.install_ok is True
    assert "wheelhouse" in result.reason
