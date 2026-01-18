from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PaperLinks(BaseModel):
    pdf: Optional[str] = None
    arxiv: Optional[str] = None
    hf: Optional[str] = None


class PaperInfo(BaseModel):
    id: str
    title: str
    links: PaperLinks


class RepoInfo(BaseModel):
    url: Optional[str] = None
    commit: Optional[str] = None
    candidates: List[str] = Field(default_factory=list)


class EnvInfo(BaseModel):
    python: str = "3.11"
    notes: str = ""


class RunSpec(BaseModel):
    name: str
    command: List[str]
    seeds: Optional[List[int]] = None


class EvalInfo(BaseModel):
    target_metrics: List[str] = Field(default_factory=list)


class BenchInfo(BaseModel):
    suites: List[str] = Field(
        default_factory=lambda: ["stability_3seeds", "cost_profile", "rerun_clean"]
    )


class ReproInfo(BaseModel):
    repo: RepoInfo = Field(default_factory=RepoInfo)
    env: EnvInfo = Field(default_factory=EnvInfo)
    runs: List[RunSpec] = Field(default_factory=list)


class ExperimentSpec(BaseModel):
    paper: PaperInfo
    repro: ReproInfo
    eval: EvalInfo = Field(default_factory=EvalInfo)
    bench: BenchInfo = Field(default_factory=BenchInfo)

    def ensure_default_run(self) -> None:
        if not self.repro.runs:
            self.repro.runs.append(
                RunSpec(name="smoke", command=["python", "-c", "print('smoke ok')"])
            )
