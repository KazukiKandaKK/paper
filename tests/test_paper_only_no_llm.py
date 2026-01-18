from pathlib import Path

import yaml

from paper2exp.core.models import ExperimentSpec
from paper2exp.core.paper_only.runner import run_paper_only


def _write_spec(run_dir: Path) -> None:
    spec = ExperimentSpec.model_validate(
        {
            "paper": {"id": "arxiv:0000.0003", "title": "", "links": {"arxiv": "", "pdf": "", "hf": None}},
            "repro": {"repo": {"url": None, "commit": None, "candidates": []}, "env": {"python": "3.11", "notes": ""}, "runs": []},
            "eval": {"target_metrics": []},
            "bench": {"suites": ["stability_3seeds", "cost_profile", "rerun_clean"]},
        }
    )
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)
    (run_dir / "repro" / "spec.yaml").write_text(
        yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8"
    )


def test_paper_only_no_llm(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "paper").mkdir(parents=True, exist_ok=True)
    (run_dir / "paper" / "metadata.json").write_text(
        '{"id":"arxiv:0000.0003","links":{}}', encoding="utf-8"
    )
    code_dir = run_dir / "code"
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "README.md").write_text("python -m train.py\n", encoding="utf-8")
    (code_dir / "train.py").write_text("print('train')\n", encoding="utf-8")
    _write_spec(run_dir)

    result = run_paper_only(run_dir, no_llm=True, llm="none")
    out_dir = run_dir / "paper_only"
    assert (out_dir / "facts.json").exists()
    assert (out_dir / "insights.json").exists()
    assert (out_dir / "applications.json").exists()
    assert (out_dir / "report.md").exists()
    assert result["applications"]["applications"]
