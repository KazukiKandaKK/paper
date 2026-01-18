from __future__ import annotations

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from paper2exp.core.llm.agent_prompts import AGENT_OUTPUT_JSON_SCHEMA


def validate_agent_output(payload: dict) -> tuple[bool, str]:
    try:
        Draft202012Validator(AGENT_OUTPUT_JSON_SCHEMA).validate(payload)
    except ValidationError as exc:
        return False, str(exc)
    return True, ""
