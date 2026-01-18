from pathlib import Path

import paper2exp.core.pipeline as pipeline
from paper2exp.core.ingest.service import PaperMetadata
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
            "stderr_tail": "Permission denied",
        }


def test_repo_auth_fallback_status(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PAPER2EXP_NOW", "20260118_150000")
    monkeypatch.setattr(pipeline, "Runner", DummyRunner)
    monkeypatch.setattr(
        pipeline,
        "ingest_paper",
        lambda *args, **kwargs: PaperMetadata(
            id="arxiv:2511.14460",
            title="",
            summary="",
            links={"arxiv": "https://arxiv.org/abs/2511.14460", "pdf": "https://arxiv.org/pdf/2511.14460.pdf", "hf": None},
            arxiv_id="2511.14460",
            repo_candidates=[],
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "validate_candidates",
        lambda urls, runner: [
            ValidationResult(
                url=u,
                status="auth_or_permission",
                stdout_tail="",
                stderr_tail="could not read Username",
            )
            for u in urls
        ],
    )

    run_dir = pipeline.run_pipeline(
        "https://arxiv.org/abs/2511.14460",
        workdir=tmp_path,
        no_exec=False,
        allow_network=True,
        agent=True,
        llm="none",
    )
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "- repo_cloned: False" in summary
    assert "- repro_executed: False" in summary
    assert "- repro_verified: None" in summary
    assert "- paper_to_code_generated: True" in summary
    assert "Official reproduction: NOT RUN" in summary
