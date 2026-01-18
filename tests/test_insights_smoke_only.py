from pathlib import Path

from paper2exp.core.insights.runner import run_insights
from paper2exp.core.models import ExperimentSpec


def test_insights_smoke_only(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)
    (run_dir / "code" / ".git").mkdir(parents=True, exist_ok=True)
    (run_dir / "repro" / "results.jsonl").write_text(
        '{"id":1,"command":["python","-c","print(\'smoke ok\')"],"exit_code":0,"stdout_tail":"smoke ok"}\n',
        encoding="utf-8",
    )
    spec = ExperimentSpec.model_validate(
        {
            "paper": {"id": "arxiv:1", "title": "", "links": {"arxiv": "", "pdf": "", "hf": None}},
            "repro": {"repo": {"url": None, "commit": None, "candidates": []}, "env": {"python": "3.11", "notes": ""}, "runs": []},
            "eval": {"target_metrics": []},
            "bench": {"suites": ["stability_3seeds", "cost_profile", "rerun_clean"]},
        }
    )
    insights = run_insights(
        run_dir,
        spec,
        llm="none",
        llm_model="",
        insights_no_llm=True,
    )
    assert insights["maturity"]["level"] == "L1_SMOKE"
