from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import yaml

from paper2exp.core.llm.agent_prompts import (
    AGENT_OUTPUT_JSON_SCHEMA,
    DEFAULT_ALLOWLIST_EXECUTABLES,
    EXTRACT_PROMPT_TEMPLATE,
    REPAIR_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
)
from paper2exp.core.llm.apply_patch import PatchDecision, apply_agent_output
from paper2exp.core.llm.base import LLMClient
from paper2exp.core.llm.chunking import chunk_text, format_chunks
from paper2exp.core.llm.validate import validate_agent_output
from paper2exp.core.models import ExperimentSpec
from paper2exp.core.utils import write_text


class NoopLLMClient(LLMClient):
    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> dict:
        return {
            "mode": "extract",
            "patches": [],
            "evidence": [],
            "suggested_commands": [],
            "missing_info": [],
            "conflicts": [],
            "stop": True,
            "stop_reason": "noop",
        }


def get_llm_client(llm: str) -> LLMClient:
    if llm == "gemini":
        from paper2exp.core.llm.gemini_vertex import GeminiVertexClient

        return GeminiVertexClient()
    return NoopLLMClient()


def run_llm_extract(
    spec: ExperimentSpec,
    *,
    paper_id: str,
    arxiv_url: str | None,
    pdf_url: str | None,
    paper_title: str,
    paper_text: str,
    llm: str,
    model: str,
    run_dir: Path,
    allowlist: Optional[set[str]] = None,
    llm_client: Optional[LLMClient] = None,
) -> tuple[ExperimentSpec, PatchDecision]:
    llm_dir = run_dir / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    allowlist = allowlist or set(DEFAULT_ALLOWLIST_EXECUTABLES)
    chunks = chunk_text(paper_text)
    chunked_text = format_chunks(chunks)
    current_spec_yaml = yaml.safe_dump(spec.model_dump(), sort_keys=False)
    prompt = "\n\n".join(
        [
            SYSTEM_PROMPT,
            EXTRACT_PROMPT_TEMPLATE.format(
                paper_id=paper_id,
                arxiv_url=arxiv_url or "",
                pdf_url=pdf_url or "",
                current_title=paper_title,
                current_spec_yaml=current_spec_yaml,
                chunked_text_with_ids=chunked_text,
            ),
        ]
    )
    write_text(llm_dir / "prompt.txt", prompt)
    (llm_dir / "schema.json").write_text(
        json.dumps(AGENT_OUTPUT_JSON_SCHEMA, indent=2), encoding="utf-8"
    )
    if llm_client is None:
        llm_client = get_llm_client(llm)
    response = llm_client.generate_structured(
        prompt, AGENT_OUTPUT_JSON_SCHEMA, model=model, temperature=0.0
    )
    (llm_dir / "response.json").write_text(
        json.dumps(response, indent=2), encoding="utf-8"
    )
    ok, err = validate_agent_output(response)
    if not ok:
        decision = PatchDecision(
            applied_patches=[],
            rejected_patches=[{"reason": f"schema validation failed: {err}"}],
            accepted_suggestions=[],
            rejected_suggestions=[],
            missing_info=[],
            conflicts=[],
            stop=True,
            stop_reason="invalid LLM response schema",
        )
        _write_decision(llm_dir, decision)
        return spec, decision
    if response.get("mode") != "extract":
        decision = PatchDecision(
            applied_patches=[],
            rejected_patches=[{"reason": "mode must be extract"}],
            accepted_suggestions=[],
            rejected_suggestions=[],
            missing_info=response.get("missing_info", []),
            conflicts=response.get("conflicts", []),
            stop=True,
            stop_reason="invalid LLM mode",
        )
        _write_decision(llm_dir, decision)
        return spec, decision
    if response.get("suggested_commands"):
        response["suggested_commands"] = []
    spec, decision = apply_agent_output(
        spec,
        response,
        text_corpus=paper_text,
        allowlist=allowlist,
        allow_network=False,
        allow_package_install=False,
        allow_write_repo=False,
    )
    _write_decision(llm_dir, decision)
    return spec, decision


def run_llm_repair(
    spec: ExperimentSpec,
    *,
    repo_file_index: str,
    repo_file_snippets: str,
    last_results_jsonl_lines: str,
    stderr_tail: str,
    stdout_tail: str,
    bench_report_md: str,
    llm: str,
    model: str,
    run_dir: Path,
    allowlist: set[str],
    allow_network: bool,
    allow_package_install: bool,
    allow_write_repo: bool,
    max_steps: int,
    step_index: int,
    llm_client: Optional[LLMClient] = None,
) -> tuple[ExperimentSpec, PatchDecision]:
    llm_dir = run_dir / "llm" / f"repair_step_{step_index}"
    llm_dir.mkdir(parents=True, exist_ok=True)
    current_spec_yaml = yaml.safe_dump(spec.model_dump(), sort_keys=False)
    prompt = "\n\n".join(
        [
            SYSTEM_PROMPT,
            REPAIR_PROMPT_TEMPLATE.format(
                allowlist_executables=",".join(sorted(allowlist)),
                allow_network=str(allow_network),
                allow_write_repo=str(allow_write_repo),
                allow_package_install=str(allow_package_install),
                max_steps=max_steps,
                current_spec_yaml=current_spec_yaml,
                repo_file_index=repo_file_index,
                repo_file_snippets=repo_file_snippets,
                last_results_jsonl_lines=last_results_jsonl_lines,
                stderr_tail=stderr_tail,
                stdout_tail=stdout_tail,
                bench_report_md=bench_report_md,
            ),
        ]
    )
    write_text(llm_dir / "prompt.txt", prompt)
    (llm_dir / "schema.json").write_text(
        json.dumps(AGENT_OUTPUT_JSON_SCHEMA, indent=2), encoding="utf-8"
    )
    if llm_client is None:
        llm_client = get_llm_client(llm)
    response = llm_client.generate_structured(
        prompt, AGENT_OUTPUT_JSON_SCHEMA, model=model, temperature=0.0
    )
    (llm_dir / "response.json").write_text(
        json.dumps(response, indent=2), encoding="utf-8"
    )
    ok, err = validate_agent_output(response)
    if not ok:
        decision = PatchDecision(
            applied_patches=[],
            rejected_patches=[{"reason": f"schema validation failed: {err}"}],
            accepted_suggestions=[],
            rejected_suggestions=[],
            missing_info=[],
            conflicts=[],
            stop=True,
            stop_reason="invalid LLM response schema",
        )
        _write_decision(llm_dir, decision)
        return spec, decision
    if response.get("mode") != "repair":
        decision = PatchDecision(
            applied_patches=[],
            rejected_patches=[{"reason": "mode must be repair"}],
            accepted_suggestions=[],
            rejected_suggestions=[],
            missing_info=response.get("missing_info", []),
            conflicts=response.get("conflicts", []),
            stop=True,
            stop_reason="invalid LLM mode",
        )
        _write_decision(llm_dir, decision)
        return spec, decision
    spec, decision = apply_agent_output(
        spec,
        response,
        text_corpus="\n".join(
            [
                repo_file_snippets,
                last_results_jsonl_lines,
                stderr_tail,
                stdout_tail,
                bench_report_md,
            ]
        ),
        allowlist=allowlist,
        allow_network=allow_network,
        allow_package_install=allow_package_install,
        allow_write_repo=allow_write_repo,
    )
    _write_decision(llm_dir, decision)
    return spec, decision


def _write_decision(llm_dir: Path, decision: PatchDecision) -> None:
    decision_lines = [
        "# LLM Patch Decision",
        "",
        "## Applied Patches",
        json.dumps(decision.applied_patches, indent=2),
        "",
        "## Rejected Patches",
        json.dumps(decision.rejected_patches, indent=2),
        "",
        "## Accepted Suggestions",
        json.dumps(decision.accepted_suggestions, indent=2),
        "",
        "## Rejected Suggestions",
        json.dumps(decision.rejected_suggestions, indent=2),
        "",
        "## Missing Info",
        json.dumps(decision.missing_info, indent=2),
        "",
        "## Conflicts",
        json.dumps(decision.conflicts, indent=2),
        "",
        "## Stop",
        str(decision.stop),
        "",
        "## Stop Reason",
        decision.stop_reason,
    ]
    write_text(llm_dir / "decision.md", "\n".join(decision_lines))
