from pathlib import Path

import yaml

from paper2exp.core.models import ExperimentSpec
from paper2exp.core.paper_only.runner import run_paper_only


def _write_spec(run_dir: Path) -> None:
    spec = ExperimentSpec.model_validate(
        {
            "paper": {"id": "arxiv:0000.0004", "title": "", "links": {"arxiv": "", "pdf": "", "hf": None}},
            "repro": {"repo": {"url": None, "commit": None, "candidates": []}, "env": {"python": "3.11", "notes": ""}, "runs": []},
            "eval": {"target_metrics": []},
            "bench": {"suites": ["stability_3seeds", "cost_profile", "rerun_clean"]},
        }
    )
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)
    (run_dir / "repro" / "spec.yaml").write_text(
        yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8"
    )


def test_paper_only_blockers(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "paper").mkdir(parents=True, exist_ok=True)
    (run_dir / "paper" / "metadata.json").write_text(
        '{"id":"arxiv:0000.0004","links":{}}', encoding="utf-8"
    )
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)
    (run_dir / "repro" / "results.jsonl").write_text(
        '{"id":1,"command":["python","-m","pytest","-q"],"exit_code":1,"stderr_tail":"No module named pytest"}\n',
        encoding="utf-8",
    )
    _write_spec(run_dir)

    result = run_paper_only(run_dir, no_llm=True, llm="none")
    blockers = result["insights"]["blockers"]
    assert any(b["kind"] == "missing_dependency" for b in blockers)
