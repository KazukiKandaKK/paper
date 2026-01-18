import json
from pathlib import Path

from paper2exp.core.insights.runner import run_insights
from paper2exp.core.models import ExperimentSpec
from paper2exp.core.llm.base import LLMClient


class MockLLM(LLMClient):
    def generate_structured(self, prompt: str, schema: dict, *, model: str, temperature: float = 0.0, seed=None) -> dict:
        return {
            "next_actions": [
                {
                    "title": "Provide official repo access",
                    "why": "Repo validation indicates auth required.",
                    "requires": {
                        "allow_network": True,
                        "allow_package_install": False,
                        "allow_write_repo": False,
                        "credentials_needed": True,
                    },
                    "risk": "medium",
                    "basis": "inference",
                    "signal_ids": ["S1"],
                    "needs_approval": True,
                }
            ],
            "applications": [
                {
                    "domain": "Automation",
                    "proposal": "Apply evidence-gated repo checks to other experiments.",
                    "why_it_fits": "Run shows auth barrier; gating generalizes to similar repos.",
                    "prerequisites": ["access to official repos"],
                    "risk": "low",
                    "basis": "inference",
                    "signal_ids": ["S1"],
                }
            ],
        }


def test_insights_auth_fallback(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "repo").mkdir(parents=True, exist_ok=True)
    (run_dir / "paper").mkdir(parents=True, exist_ok=True)
    (run_dir / "paper_to_code").mkdir(parents=True, exist_ok=True)
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)

    (run_dir / "paper" / "metadata.json").write_text(
        json.dumps({"id": "arxiv:1234.5678", "links": {}}), encoding="utf-8"
    )
    (run_dir / "summary.md").write_text(
        "# Run Summary\n\n- repo_cloned: False\n- repro_executed: False\n- repro_verified: None\n",
        encoding="utf-8",
    )
    (run_dir / "repo" / "validation.json").write_text(
        json.dumps(
            {"results": [{"status": "auth_or_permission", "stderr_tail": "could not read Username"}]}
        ),
        encoding="utf-8",
    )
    (run_dir / "paper_to_code" / "plan.md").write_text("- fallback generated\n", encoding="utf-8")
    (run_dir / "paper_to_code" / "todo.md").write_text("- [ ] todo\n", encoding="utf-8")

    spec = ExperimentSpec.model_validate(
        {
            "paper": {"id": "arxiv:1234.5678", "title": "", "links": {"arxiv": "", "pdf": "", "hf": None}},
            "repro": {"repo": {"url": None, "commit": None, "candidates": []}, "env": {"python": "3.11", "notes": ""}, "runs": []},
            "eval": {"target_metrics": []},
            "bench": {"suites": ["stability_3seeds", "cost_profile", "rerun_clean"]},
        }
    )
    insights = run_insights(
        run_dir,
        spec,
        llm="gemini",
        llm_model="dummy",
        insights_no_llm=False,
        llm_client=MockLLM(),
    )
    assert insights["maturity"]["level"] == "L0_NOT_RUNNABLE"
    assert any(b["kind"] == "auth" for b in insights["blockers"])
    assert insights["applications"]
    assert insights["applications"][0]["basis"] == "inference"
