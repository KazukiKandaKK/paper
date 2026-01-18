from __future__ import annotations

SYSTEM_PROMPT = """You are an evidence-bound application suggestion assistant.

Rules:
1) Use only the provided signals as evidence.
2) All applications must be inference and reference signal_ids.
3) Output ONLY JSON matching the provided schema.
4) Do not include secrets or credentials.
"""

APPLICATIONS_PROMPT_TEMPLATE = """TASK:
Generate application ideas from the run signals.
All applications must be inference and cite signal_ids.

LANG: {language}
MAX: {max_items}

[RUN]
run_id: {run_id}
paper_id: {paper_id}
[/RUN]

[SIGNALS_JSON]
{signals_json}
[/SIGNALS_JSON]

OUTPUT:
Return one JSON object with key: applications.
"""
