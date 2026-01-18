from pathlib import Path

from paper2exp.core.insights.runner import run_insights
from paper2exp.core.models import ExperimentSpec


def test_insights_no_llm(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)
    spec = ExperimentSpec.model_validate(
        {
            "paper": {"id": "arxiv:1", "title": "", "links": {"arxiv": "", "pdf": "", "hf": None}},
            "repro": {"repo": {"url": None, "commit": None, "candidates": []}, "env": {"python": "3.11", "notes": ""}, "runs": []},
            "eval": {"target_metrics": []},
            "bench": {"suites": ["stability_3seeds", "cost_profile", "rerun_clean"]},
        }
    )
    run_insights(
        run_dir,
        spec,
        llm="none",
        llm_model="",
        insights_no_llm=True,
    )
    assert (run_dir / "insights" / "insights.json").exists()
    assert (run_dir / "insights" / "insights.md").exists()
