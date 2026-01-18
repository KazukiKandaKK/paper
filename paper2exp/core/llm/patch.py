from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paper2exp.core.models import ExperimentSpec, RunSpec


@dataclass
class PatchDecision:
    applied: dict
    rejected: dict


def apply_llm_patch(
    spec: ExperimentSpec,
    response: dict,
    paper_text: str,
    allow_new_commands: bool,
    allowlist: set[str],
) -> tuple[ExperimentSpec, PatchDecision]:
    patch = response.get("patch", {}) if isinstance(response, dict) else {}
    evidence_list = response.get("evidence", []) if isinstance(response, dict) else []
    evidence_map = _group_evidence(evidence_list)
    applied: dict[str, Any] = {}
    rejected: dict[str, str] = {}

    paper_text_l = paper_text.lower() if paper_text else ""

    # repo.url
    repo_url = _get(patch, ["repro", "repo", "url"])
    if repo_url is not None:
        if not _has_evidence(evidence_map, "repro.repo.url"):
            rejected["repro.repo.url"] = "no evidence"
        elif repo_url and repo_url.lower() not in paper_text_l:
            rejected["repro.repo.url"] = "url not found in text"
        else:
            spec.repro.repo.url = repo_url
            applied["repro.repo.url"] = repo_url

    # repo.candidates
    candidates = _get(patch, ["repro", "repo", "candidates"])
    if candidates is not None:
        if not _has_evidence(evidence_map, "repro.repo.candidates"):
            rejected["repro.repo.candidates"] = "no evidence"
        else:
            filtered = [c for c in candidates if c and c.lower() in paper_text_l]
            spec.repro.repo.candidates = filtered
            applied["repro.repo.candidates"] = filtered

    # repro.env.notes
    notes = _get(patch, ["repro", "env", "notes"])
    if notes is not None:
        if not _has_evidence(evidence_map, "repro.env.notes"):
            rejected["repro.env.notes"] = "no evidence"
        elif notes and notes.lower() not in paper_text_l:
            rejected["repro.env.notes"] = "notes not found in text"
        else:
            spec.repro.env.notes = notes
            applied["repro.env.notes"] = notes

    # eval.target_metrics
    metrics = _get(patch, ["eval", "target_metrics"])
    if metrics is not None:
        if not _has_evidence(evidence_map, "eval.target_metrics"):
            rejected["eval.target_metrics"] = "no evidence"
        else:
            filtered = [m for m in metrics if m and m.lower() in paper_text_l]
            spec.eval.target_metrics = filtered
            applied["eval.target_metrics"] = filtered

    # repro.runs
    runs = _get(patch, ["repro", "runs"])
    if runs is not None:
        if not _has_evidence(evidence_map, "repro.runs"):
            rejected["repro.runs"] = "no evidence"
        else:
            validated_runs = _validate_runs(
                runs,
                paper_text_l,
                allow_new_commands=allow_new_commands,
                allowlist=allowlist,
                rejected=rejected,
            )
            if validated_runs:
                spec.repro.runs = validated_runs
                applied["repro.runs"] = [r.model_dump() for r in validated_runs]

    return spec, PatchDecision(applied=applied, rejected=rejected)


def _group_evidence(evidence_list: list[dict]) -> dict[str, list[dict]]:
    evidence_map: dict[str, list[dict]] = {}
    for item in evidence_list:
        field = item.get("field")
        if not field:
            continue
        evidence_map.setdefault(field, []).append(item)
    return evidence_map


def _has_evidence(evidence_map: dict[str, list[dict]], field: str) -> bool:
    return bool(evidence_map.get(field))


def _validate_runs(
    runs: list[dict],
    paper_text_l: str,
    allow_new_commands: bool,
    allowlist: set[str],
    rejected: dict[str, str],
) -> list[RunSpec]:
    validated: list[RunSpec] = []
    for idx, run in enumerate(runs):
        name = run.get("name")
        command = run.get("command")
        if not name or not isinstance(command, list) or not command:
            rejected[f"repro.runs[{idx}]"] = "invalid run"
            continue
        cmd_str = " ".join(str(token) for token in command)
        if cmd_str.lower() not in paper_text_l:
            rejected[f"repro.runs[{idx}]"] = "command not found in text"
            continue
        if not allow_new_commands:
            rejected[f"repro.runs[{idx}]"] = "new commands disabled"
            continue
        if command[0] not in allowlist:
            rejected[f"repro.runs[{idx}]"] = "command not in allowlist"
            continue
        validated.append(RunSpec(name=name, command=[str(t) for t in command], seeds=run.get("seeds")))
    return validated


def _get(data: dict, path: list[str]) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur
