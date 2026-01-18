from pathlib import Path

from typer.testing import CliRunner

import paper2exp.core.ingest.arxiv as arxiv_ingest
import paper2exp.core.pipeline as pipeline
from paper2exp.cli import app
from paper2exp.core.llm.base import LLMClient
import paper2exp.core.llm.manager as llm_manager


runner = CliRunner()


class MockLLM(LLMClient):
    def generate_structured(self, prompt: str, schema: dict, *, model: str, temperature: float = 0.0, seed=None) -> dict:
        return {
            "mode": "extract",
            "patches": [],
            "evidence": [],
            "suggested_commands": [],
            "missing_info": [],
            "conflicts": [],
            "stop": True,
            "stop_reason": "noop",
        }


def test_llm_gemini_requires_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    result = runner.invoke(
        app,
        [
            "run",
            "https://arxiv.org/abs/2511.14460",
            "--no-exec",
            "--llm",
            "gemini",
            "--download-pdf",
            "--workdir",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0
    assert "Missing env vars for Gemini" in result.output


def test_no_exec_does_not_create_llm_or_pdf(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PAPER2EXP_NOW", "20260118_130000")
    result = runner.invoke(
        app,
        [
            "run",
            "https://arxiv.org/abs/2511.14460",
            "--no-exec",
            "--workdir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    run_dir = Path(result.output.strip())
    assert not (run_dir / "paper" / "paper.pdf").exists()
    assert not (run_dir / "llm").exists()


def test_no_exec_llm_pdf_creates_llm(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "dummy")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "dummy")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("PAPER2EXP_NOW", "20260118_130001")

    def fake_download(url, dest_path):
        dest_path.write_bytes(b"pdf")
        return True

    monkeypatch.setattr(arxiv_ingest, "download_pdf", fake_download)
    monkeypatch.setattr(
        pipeline,
        "extract_text_from_pdf",
        lambda path: "Code: https://github.com/org/repo",
    )
    monkeypatch.setattr(llm_manager, "get_llm_client", lambda llm: MockLLM())

    result = runner.invoke(
        app,
        [
            "run",
            "https://arxiv.org/abs/2511.14460",
            "--no-exec",
            "--llm",
            "gemini",
            "--download-pdf",
            "--workdir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    run_dir = Path(result.output.strip())
    assert (run_dir / "paper" / "paper.pdf").exists()
    llm_dir = run_dir / "llm"
    assert (llm_dir / "prompt.txt").exists()
    assert (llm_dir / "schema.json").exists()
    assert (llm_dir / "response.json").exists()
    assert (llm_dir / "decision.md").exists()
