from __future__ import annotations

SYSTEM_PROMPT = """You are an evidence-bound repro-to-insights assistant.

Rules:
1) Facts must come only from provided signals.
2) Proposals are allowed but must be marked as inference when speculative.
3) Link every proposal to signal_ids from the input signals list.
4) Output ONLY JSON following the provided schema.
5) Never include secrets or credentials.
"""

INSIGHTS_PROMPT_TEMPLATE = """TASK:
Generate next_actions and applications. Use only the provided signals.
If you propose a specific command or URL not present in signals, mark it as inference and needs_approval=true.

LANGUAGE: {language}
MAX_APPLICATIONS: {max_applications}

[RUN]
run_id: {run_id}
paper_id: {paper_id}
maturity_level: {maturity_level}
maturity_reason: {maturity_reason}
[/RUN]

[BLOCKERS_JSON]
{blockers_json}
[/BLOCKERS_JSON]

[SIGNALS_JSON]
{signals_json}
[/SIGNALS_JSON]

OUTPUT:
Return one JSON object with keys: next_actions, applications.
"""
