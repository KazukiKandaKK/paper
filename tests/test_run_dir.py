from pathlib import Path

from paper2exp.core.pipeline import run_pipeline


def test_run_dir_artifacts(tmp_path: Path):
    run_dir = run_pipeline("https://arxiv.org/abs/2511.14460", workdir=tmp_path, no_exec=True)
    required = [
        "paper/metadata.json",
        "repro/spec.yaml",
        "repro/run.sh",
        "repro/results.jsonl",
        "repro/compare.md",
        "summary.md",
        "bench/report.md",
        "bench/results.json",
    ]
    for rel in required:
        assert (run_dir / rel).exists(), f"missing {rel}"
