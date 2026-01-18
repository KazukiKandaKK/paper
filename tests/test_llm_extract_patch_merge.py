from paper2exp.core.llm.apply_patch import apply_agent_output
from paper2exp.core.models import (
    BenchInfo,
    EnvInfo,
    EvalInfo,
    ExperimentSpec,
    PaperInfo,
    PaperLinks,
    RepoInfo,
    ReproInfo,
    RunSpec,
)


def _base_spec():
    return ExperimentSpec(
        paper=PaperInfo(
            id="arxiv:2511.14460",
            title="",
            links=PaperLinks(pdf="https://arxiv.org/pdf/2511.14460.pdf", arxiv=None, hf=None),
        ),
        repro=ReproInfo(
            repo=RepoInfo(url=None, commit=None, candidates=[]),
            env=EnvInfo(python="3.11", notes=""),
            runs=[RunSpec(name="smoke", command=["python", "-c", "print('smoke ok')"])],
        ),
        eval=EvalInfo(target_metrics=[]),
        bench=BenchInfo(),
    )


def test_apply_patch_with_evidence_and_text():
    paper_text = (
        "Code: https://github.com/org/repo\n"
        "Run: python -c print('ok')\n"
        "Metric: accuracy\n"
        "Notes: use default config.\n"
    )
    agent_output = {
        "mode": "extract",
        "patches": [
            {
                "op": "set",
                "path": "/repro/repo/url",
                "value": "https://github.com/org/repo",
                "basis": "paper_quote",
                "evidence_ids": ["E1"],
            },
            {
                "op": "set",
                "path": "/repro/repo/candidates",
                "value": ["https://github.com/org/repo", "https://github.com/other/repo"],
                "basis": "paper_quote",
                "evidence_ids": ["E1"],
            },
            {
                "op": "set",
                "path": "/repro/runs",
                "value": [
                    {"name": "main", "command": ["python", "-c", "print('ok')"], "seeds": None}
                ],
                "basis": "paper_quote",
                "evidence_ids": ["E2"],
            },
            {
                "op": "set",
                "path": "/eval/target_metrics",
                "value": ["accuracy", "f1"],
                "basis": "paper_quote",
                "evidence_ids": ["E3"],
            },
            {
                "op": "set",
                "path": "/repro/env/notes",
                "value": "use default config.",
                "basis": "paper_quote",
                "evidence_ids": ["E4"],
            },
        ],
        "evidence": [
            {"id": "E1", "source": "paper_text", "locator": "chunk:C1", "quote": "https://github.com/org/repo"},
            {"id": "E2", "source": "paper_text", "locator": "chunk:C1", "quote": "python -c print('ok')"},
            {"id": "E3", "source": "paper_text", "locator": "chunk:C1", "quote": "accuracy"},
            {"id": "E4", "source": "paper_text", "locator": "chunk:C1", "quote": "use default config."},
        ],
        "suggested_commands": [],
        "missing_info": [],
        "conflicts": [],
        "stop": False,
        "stop_reason": "",
    }
    spec = _base_spec()
    spec, decision = apply_agent_output(
        spec,
        agent_output,
        text_corpus=paper_text,
        allowlist={"python"},
        allow_network=False,
        allow_package_install=False,
        allow_write_repo=False,
    )
    assert spec.repro.repo.url == "https://github.com/org/repo"
    assert spec.repro.repo.candidates == ["https://github.com/org/repo"]
    assert spec.repro.runs[0].name == "main"
    assert spec.repro.runs[0].command == ["python", "-c", "print('ok')"]
    assert spec.eval.target_metrics == ["accuracy"]
    assert spec.repro.env.notes == "use default config."
    assert decision.applied_patches


def test_reject_without_evidence_or_text():
    paper_text = "No repo here."
    agent_output = {
        "mode": "extract",
        "patches": [
            {
                "op": "set",
                "path": "/repro/repo/url",
                "value": "https://github.com/org/repo",
                "basis": "paper_quote",
                "evidence_ids": ["E1"],
            }
        ],
        "evidence": [],
        "suggested_commands": [],
        "missing_info": [],
        "conflicts": [],
        "stop": False,
        "stop_reason": "",
    }
    spec = _base_spec()
    spec, decision = apply_agent_output(
        spec,
        agent_output,
        text_corpus=paper_text,
        allowlist={"python"},
        allow_network=False,
        allow_package_install=False,
        allow_write_repo=False,
    )
    assert spec.repro.repo.url is None
    assert decision.rejected_patches


def test_reject_url_not_in_text():
    paper_text = "No repo here."
    agent_output = {
        "mode": "extract",
        "patches": [
            {
                "op": "set",
                "path": "/repro/repo/url",
                "value": "https://github.com/org/repo",
                "basis": "paper_quote",
                "evidence_ids": ["E1"],
            }
        ],
        "evidence": [
            {
                "id": "E1",
                "source": "paper_text",
                "locator": "chunk:C1",
                "quote": "https://github.com/org/repo",
            }
        ],
        "suggested_commands": [],
        "missing_info": [],
        "conflicts": [],
        "stop": False,
        "stop_reason": "",
    }
    spec = _base_spec()
    spec, decision = apply_agent_output(
        spec,
        agent_output,
        text_corpus=paper_text,
        allowlist={"python"},
        allow_network=False,
        allow_package_install=False,
        allow_write_repo=False,
    )
    assert spec.repro.repo.url is None
    assert decision.rejected_patches
