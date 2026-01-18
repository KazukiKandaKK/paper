from __future__ import annotations

from paper2exp.core.models import ExperimentSpec


def build_prompt(spec: ExperimentSpec, paper_text: str, extra_context: str | None = None) -> str:
    rules = [
        "You are extracting reproducible experiment specs from a paper.",
        "Do NOT guess. If the paper does not explicitly state a value, return null/empty.",
        "Only include repo URLs and commands that appear verbatim in the paper text.",
        "Return JSON matching the response_schema.",
    ]
    spec_block = spec.model_dump()
    prompt = [
        "System rules:",
        *rules,
        "",
        "Current spec (baseline):",
        str(spec_block),
        "",
        "Paper text:",
        paper_text,
    ]
    if extra_context:
        prompt.extend(["", "Execution context:", extra_context])
    return "\n".join(prompt)
