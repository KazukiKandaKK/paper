from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paper2exp.core.models import ExperimentSpec, RunSpec


@dataclass
class PatchDecision:
    applied_patches: list[dict]
    rejected_patches: list[dict]
    accepted_suggestions: list[dict]
    rejected_suggestions: list[dict]
    missing_info: list[str]
    conflicts: list[dict]
    stop: bool
    stop_reason: str


def apply_agent_output(
    spec: ExperimentSpec,
    agent_output: dict,
    *,
    text_corpus: str,
    allowlist: set[str],
    allow_network: bool,
    allow_package_install: bool,
    allow_write_repo: bool,
) -> tuple[ExperimentSpec, PatchDecision]:
    evidence_map = {e.get("id"): e for e in agent_output.get("evidence", [])}
    patches = agent_output.get("patches", [])
    suggestions = agent_output.get("suggested_commands", [])

    applied: list[dict] = []
    rejected: list[dict] = []
    accepted_suggestions: list[dict] = []
    rejected_suggestions: list[dict] = []

    corpus = (text_corpus or "").lower()

    for patch in patches:
        reason = _validate_patch(patch, evidence_map, corpus, allowlist)
        if reason:
            rejected.append({"patch": patch, "reason": reason})
            continue
        _apply_patch_to_spec(spec, patch, evidence_map, corpus, applied, rejected)

    for suggestion in suggestions:
        decision, adjusted = _validate_suggestion(
            suggestion,
            evidence_map,
            allowlist,
            allow_network=allow_network,
            allow_package_install=allow_package_install,
            allow_write_repo=allow_write_repo,
        )
        if decision == "accept":
            accepted_suggestions.append(adjusted)
        else:
            rejected_suggestions.append({"suggestion": suggestion, "reason": decision})

    return spec, PatchDecision(
        applied_patches=applied,
        rejected_patches=rejected,
        accepted_suggestions=accepted_suggestions,
        rejected_suggestions=rejected_suggestions,
        missing_info=agent_output.get("missing_info", []),
        conflicts=agent_output.get("conflicts", []),
        stop=bool(agent_output.get("stop")),
        stop_reason=agent_output.get("stop_reason", ""),
    )


def _validate_patch(
    patch: dict,
    evidence_map: dict[str, dict],
    corpus: str,
    allowlist: set[str],
) -> str | None:
    if patch.get("basis") == "inference":
        return "basis=inference not allowed for patches"
    evidence_ids = patch.get("evidence_ids", [])
    if not evidence_ids:
        return "missing evidence"
    if not any(eid in evidence_map for eid in evidence_ids):
        return "evidence ids not found"
    path = patch.get("path")
    if path not in {
        "/repro/repo/url",
        "/repro/repo/candidates",
        "/repro/runs",
        "/eval/target_metrics",
        "/repro/env/notes",
    }:
        return "unsupported path"
    if path == "/repro/runs":
        runs = patch.get("value")
        if not isinstance(runs, list) or not runs:
            return "runs must be non-empty list"
        for run in runs:
            cmd = run.get("command") if isinstance(run, dict) else None
            if not cmd or not isinstance(cmd, list) or not cmd:
                return "invalid run command"
            if cmd[0] not in allowlist:
                return "command not in allowlist"
    return None


def _apply_patch_to_spec(
    spec: ExperimentSpec,
    patch: dict,
    evidence_map: dict[str, dict],
    corpus: str,
    applied: list[dict],
    rejected: list[dict],
) -> None:
    path = patch.get("path")
    op = patch.get("op")
    value = patch.get("value")
    evidence_ids = patch.get("evidence_ids", [])
    evidence_items = [evidence_map[eid] for eid in evidence_ids if eid in evidence_map]

    if path == "/repro/repo/url":
        if not _evidence_contains_value(evidence_items, value):
            rejected.append({"patch": patch, "reason": "url not in evidence"})
            return
        if value and value.lower() not in corpus:
            rejected.append({"patch": patch, "reason": "url not found in text"})
            return
        if op in {"set", "append"}:
            spec.repro.repo.url = value
            applied.append(patch)
            return
        if op == "remove":
            spec.repro.repo.url = None
            applied.append(patch)
            return

    if path == "/repro/repo/candidates":
        if not isinstance(value, list):
            rejected.append({"patch": patch, "reason": "candidates must be list"})
            return
        filtered = []
        for candidate in value:
            if not _evidence_contains_value(evidence_items, candidate):
                continue
            if candidate and candidate.lower() not in corpus:
                continue
            filtered.append(candidate)
        if not filtered:
            rejected.append({"patch": patch, "reason": "no candidates validated"})
            return
        if op == "set":
            spec.repro.repo.candidates = filtered
        elif op == "append":
            spec.repro.repo.candidates.extend(
                [c for c in filtered if c not in spec.repro.repo.candidates]
            )
        elif op == "remove":
            spec.repro.repo.candidates = []
        applied.append(patch)
        return

    if path == "/eval/target_metrics":
        if not isinstance(value, list):
            rejected.append({"patch": patch, "reason": "target_metrics must be list"})
            return
        filtered = []
        for metric in value:
            if not _evidence_contains_value(evidence_items, metric):
                continue
            if metric and metric.lower() not in corpus:
                continue
            filtered.append(metric)
        if op == "set":
            spec.eval.target_metrics = filtered
        elif op == "append":
            for metric in filtered:
                if metric not in spec.eval.target_metrics:
                    spec.eval.target_metrics.append(metric)
        elif op == "remove":
            spec.eval.target_metrics = []
        applied.append(patch)
        return

    if path == "/repro/env/notes":
        if not _evidence_contains_value(evidence_items, value):
            rejected.append({"patch": patch, "reason": "notes not in evidence"})
            return
        if value and value.lower() not in corpus:
            rejected.append({"patch": patch, "reason": "notes not found in text"})
            return
        if op in {"set", "append"}:
            spec.repro.env.notes = value or ""
            applied.append(patch)
            return
        if op == "remove":
            spec.repro.env.notes = ""
            applied.append(patch)
            return

    if path == "/repro/runs":
        if not isinstance(value, list) or not value:
            rejected.append({"patch": patch, "reason": "runs must be list"})
            return
        validated: list[RunSpec] = []
        for run in value:
            name = run.get("name")
            command = run.get("command")
            if not name or not isinstance(command, list) or not command:
                continue
            cmd_str = " ".join(str(token) for token in command)
            if not _evidence_contains_value(evidence_items, cmd_str):
                continue
            if cmd_str.lower() not in corpus:
                continue
            validated.append(
                RunSpec(
                    name=name,
                    command=[str(token) for token in command],
                    seeds=run.get("seeds"),
                )
            )
        if not validated:
            rejected.append({"patch": patch, "reason": "no valid runs"})
            return
        if op in {"set", "append"}:
            spec.repro.runs = validated
        elif op == "remove":
            spec.repro.runs = []
        applied.append(patch)
        return

    rejected.append({"patch": patch, "reason": "unsupported patch"})


def _evidence_contains_value(evidence_items: list[dict], value: Any) -> bool:
    if value is None:
        return True
    value_str = str(value)
    for item in evidence_items:
        quote = item.get("quote", "")
        if value_str in quote:
            return True
    return False


def _validate_suggestion(
    suggestion: dict,
    evidence_map: dict[str, dict],
    allowlist: set[str],
    *,
    allow_network: bool,
    allow_package_install: bool,
    allow_write_repo: bool,
) -> tuple[str, dict]:
    command = suggestion.get("command")
    if not isinstance(command, list) or not command:
        return "invalid command", suggestion
    if command[0] not in allowlist:
        return "command not in allowlist", suggestion
    evidence_ids = suggestion.get("evidence_ids", [])
    if evidence_ids and not any(eid in evidence_map for eid in evidence_ids):
        return "evidence ids not found", suggestion

    adjusted = dict(suggestion)
    if _is_package_install(command) and not allow_package_install:
        adjusted["needs_approval"] = True
    if _is_network_command(command) and not allow_network:
        adjusted["needs_approval"] = True
    if _is_repo_write(command) and not allow_write_repo:
        adjusted["needs_approval"] = True
    return "accept", adjusted


def _is_package_install(command: list[str]) -> bool:
    return command[0] in {"pip", "uv", "conda"} and "install" in command


def _is_network_command(command: list[str]) -> bool:
    if _is_package_install(command):
        return True
    return any(token.startswith("http") for token in command)


def _is_repo_write(command: list[str]) -> bool:
    return any(token in {">", "apply_patch"} for token in command)
