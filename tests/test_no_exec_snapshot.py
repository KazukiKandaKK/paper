import json
from pathlib import Path

import yaml

from paper2exp.core.pipeline import run_pipeline


def test_no_exec_outputs(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PAPER2EXP_NOW", "20260118_120000")
    run_dir = run_pipeline("https://arxiv.org/abs/2511.14460", workdir=tmp_path, no_exec=True)
    assert run_dir.name == "20260118_120000_2511.14460"

    metadata = json.loads((run_dir / "paper" / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "arxiv:2511.14460"
    assert metadata["title"] == ""
    assert metadata["summary"] == ""
    assert metadata["links"]["arxiv"] == "https://arxiv.org/abs/2511.14460"
    assert metadata["links"]["pdf"] == "https://arxiv.org/pdf/2511.14460.pdf"
    assert metadata["links"].get("hf") is None
    assert metadata["pdf_downloaded"] is False
    assert not (run_dir / "paper" / "paper.pdf").exists()
    assert not (run_dir / "llm").exists()

    spec = yaml.safe_load((run_dir / "repro" / "spec.yaml").read_text(encoding="utf-8"))
    assert spec["paper"]["id"] == "arxiv:2511.14460"
    assert spec["paper"]["title"] == ""
    assert spec["paper"]["links"]["hf"] is None
    assert spec["repro"]["repo"]["url"] is None
    assert spec["repro"]["repo"]["candidates"] == []
    assert spec["repro"]["runs"][0]["command"] == ["python", "-c", "print('smoke ok')"]

    run_sh = (run_dir / "repro" / "run.sh").read_text(encoding="utf-8").splitlines()
    command_line = next(
        line for line in run_sh if line and not line.startswith("#") and not line.startswith("set ")
    )
    assert "python -c" in command_line
    assert "smoke ok" in command_line
    assert "python -c print('smoke ok')" not in command_line

    results_line = (run_dir / "repro" / "results.jsonl").read_text(encoding="utf-8").splitlines()[0]
    record = json.loads(results_line)
    assert record["status"] == "skipped"
    assert record["duration_sec"] == 0.0
    assert record["exit_code"] is None
    assert record["stderr_tail"] == "(no-exec)"
    assert record["stdout_tail"] == ""
    assert (Path(record["stdout_path"]).exists())
    assert (Path(record["stderr_path"]).exists())

    bench_report = (run_dir / "bench" / "report.md").read_text(encoding="utf-8")
    assert bench_report.startswith("# Bench Report")
    assert "## stability_3seeds" in bench_report
    assert "{\"status\":\"skipped\",\"reason\":\"no seeds in spec\"}" in bench_report
    assert "## cost_profile" in bench_report
    assert "{\"status\":\"ok\",\"duration_sec\":0.0,\"exit_code\":null,\"rss_kb\":null}" in bench_report
    assert "## rerun_clean" in bench_report
    assert "{\"status\":\"skipped\",\"reason\":\"no-exec\"}" in bench_report

    compare_md = (run_dir / "repro" / "compare.md").read_text(encoding="utf-8")
    assert compare_md.startswith("# Reproduction Compare")
    assert "| Metric | Value |" in compare_md
    assert "| format_ok | True |" in compare_md
    assert "| exec_ok | False |" in compare_md
    assert "| rerun_ok | None |" in compare_md

    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert summary.startswith("# Run Summary")
    assert "Paper: arxiv:2511.14460" in summary
    assert "Title:" in summary
    assert "## Status" in summary
    assert "- repo_cloned: False" in summary
    assert "- exec_ok: False" in summary
    assert "## Paths" in summary
    assert f"- paper: runs/{run_dir.name}/paper" in summary
    assert f"- repro: runs/{run_dir.name}/repro" in summary
    assert f"- bench: runs/{run_dir.name}/bench" in summary
