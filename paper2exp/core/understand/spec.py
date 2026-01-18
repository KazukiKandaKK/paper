from __future__ import annotations

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
from paper2exp.core.understand.heuristics import extract_github_links, pick_primary_repo


def build_experiment_spec(
    paper_id: str,
    title: str,
    links: dict,
    text: str,
) -> ExperimentSpec:
    candidates = extract_github_links(text or "")
    primary = pick_primary_repo(candidates)
    spec = ExperimentSpec(
        paper=PaperInfo(
            id=paper_id,
            title=title,
            links=PaperLinks(
                pdf=links.get("pdf"),
                arxiv=links.get("arxiv"),
                hf=links.get("hf"),
            ),
        ),
        repro=ReproInfo(
            repo=RepoInfo(url=primary, candidates=candidates),
            env=EnvInfo(python="3.11", notes=""),
            runs=[RunSpec(name="smoke", command=["python", "-c", "print('smoke ok')"])],
        ),
        eval=EvalInfo(),
        bench=BenchInfo(),
    )
    spec.repro = spec.repro.model_copy()

    spec.ensure_default_run()
    return spec
