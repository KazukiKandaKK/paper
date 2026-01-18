from pathlib import Path
import json

from paper2exp.core.models import ExperimentSpec


def test_spec_validation():
    data = {
        "paper": {
            "id": "arxiv:2511.14460",
            "title": "Agent-R1",
            "links": {"pdf": "http://example.com"},
        },
        "repro": {
            "repo": {"url": "https://github.com/org/repo", "candidates": []},
            "env": {"python": "3.11", "notes": ""},
            "runs": [{"name": "smoke", "command": ["python", "-c", "print('ok')"]}],
        },
        "eval": {"target_metrics": []},
        "bench": {"suites": ["stability_3seeds"]},
    }
    spec = ExperimentSpec.model_validate(data)
    assert spec.paper.id == "arxiv:2511.14460"


def test_schema_file_exists():
    schema_path = Path(__file__).resolve().parents[1] / "paper2exp" / "schemas" / "experiment_spec.schema.json"
    assert schema_path.exists()
    json.loads(schema_path.read_text(encoding="utf-8"))
