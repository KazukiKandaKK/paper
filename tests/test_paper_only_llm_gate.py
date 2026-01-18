from pathlib import Path

import yaml

from paper2exp.core.llm.base import LLMClient
from paper2exp.core.models import ExperimentSpec
from paper2exp.core.paper_only.runner import run_paper_only


class MockLLM(LLMClient):
    def generate_structured(self, prompt: str, schema: dict, *, model: str, temperature: float = 0.0, seed=None) -> dict:
        return {
            "applications": [
                {
                    "domain": "test",
                    "proposal": "invalid signals",
                    "why_it_fits": "no evidence",
                    "prerequisites": [],
                    "risk": "low",
                    "basis": "inference",
                    "signal_ids": ["S999"],
                }
            ]
        }


def _write_spec(run_dir: Path) -> None:
    spec = ExperimentSpec.model_validate(
        {
            "paper": {"id": "arxiv:0000.0005", "title": "", "links": {"arxiv": "", "pdf": "", "hf": None}},
            "repro": {"repo": {"url": None, "commit": None, "candidates": []}, "env": {"python": "3.11", "notes": ""}, "runs": []},
            "eval": {"target_metrics": []},
            "bench": {"suites": ["stability_3seeds", "cost_profile", "rerun_clean"]},
        }
    )
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)
    (run_dir / "repro" / "spec.yaml").write_text(
        yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8"
    )


def test_paper_only_llm_gate(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "paper").mkdir(parents=True, exist_ok=True)
    (run_dir / "paper" / "metadata.json").write_text(
        '{"id":"arxiv:0000.0005","links":{}}', encoding="utf-8"
    )
    _write_spec(run_dir)

    result = run_paper_only(
        run_dir,
        no_llm=False,
        llm="gemini",
        llm_model="dummy",
        llm_client=MockLLM(),
    )
    # LLM invalid output should be filtered to empty applications
    assert result["applications"]["applications"] == []
