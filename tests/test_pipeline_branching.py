from pathlib import Path

import paper2exp.core.pipeline as pipeline
from paper2exp.core.repo.validate import ValidationResult


class DummyRunner:
    def __init__(self, results_path: Path, logs_dir: Path, no_exec: bool = False) -> None:
        self.results_path = results_path
        self.logs_dir = logs_dir
        self.no_exec = no_exec
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def run(self, command, cwd, timeout_sec=None):
        return {
            "id": 1,
            "command": list(command),
            "cwd": str(cwd),
            "start_time": 0.0,
            "status": "ran",
            "end_time": 0.0,
            "duration_sec": 0.0,
            "exit_code": 1,
            "stdout_path": str(self.logs_dir / "dummy.out"),
            "stderr_path": str(self.logs_dir / "dummy.err"),
            "stdout_tail": "",
            "stderr_tail": "Repository not found",
        }


def test_pipeline_branching_no_repo(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PAPER2EXP_NOW", "20260118_130500")
    monkeypatch.setattr(pipeline, "Runner", DummyRunner)
    monkeypatch.setattr(
        pipeline,
        "validate_candidates",
        lambda urls, runner: [
            ValidationResult(url=u, status="not_found", stdout_tail="", stderr_tail="Repository not found")
            for u in urls
        ],
    )
    monkeypatch.setattr(pipeline, "clone_repo", lambda url, dest, runner: False)

    run_dir = pipeline.run_pipeline(
        "https://arxiv.org/abs/2511.14460",
        workdir=tmp_path,
        no_exec=True,
        allow_network=False,
    )
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "追試未成立" in summary


def test_pipeline_paper_to_code(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PAPER2EXP_NOW", "20260118_130501")
    monkeypatch.setattr(pipeline, "Runner", DummyRunner)

    run_dir = pipeline.run_pipeline(
        "https://arxiv.org/abs/2511.14460",
        workdir=tmp_path,
        no_exec=True,
        allow_network=False,
        paper_to_code=True,
    )
    assert not (run_dir / "paper_to_code").exists()


def test_pipeline_agent_fallback_to_paper_to_code(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PAPER2EXP_NOW", "20260118_130502")
    monkeypatch.setattr(pipeline, "Runner", DummyRunner)

    run_dir = pipeline.run_pipeline(
        "https://arxiv.org/abs/2511.14460",
        workdir=tmp_path,
        no_exec=False,
        allow_network=False,
        agent=True,
        llm="none",
    )
    assert (run_dir / "paper_to_code" / "plan.md").exists()
    assert (run_dir / "paper_to_code" / "todo.md").exists()
    selection = (run_dir / "repo" / "selection.json").read_text(encoding="utf-8")
    assert "fallback" in selection
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "paper-to-codeへフォールバック" in summary
