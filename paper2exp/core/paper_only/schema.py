from __future__ import annotations

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


FACTS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["run_id", "paper_id", "paper_repo", "facts", "evidence"],
    "properties": {
        "run_id": {"type": "string"},
        "paper_id": {"type": "string"},
        "paper_repo": {"type": ["string", "null"]},
        "facts": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "entrypoints",
                "dependencies",
                "repro_steps",
                "eval_harness",
                "config_surface",
            ],
            "properties": {
                "entrypoints": {"type": "array", "items": {"type": "string"}},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "repro_steps": {"type": "array", "items": {"type": "string"}},
                "eval_harness": {"type": "array", "items": {"type": "string"}},
                "config_surface": {"type": "array", "items": {"type": "string"}},
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "source", "locator", "quote"],
                "properties": {
                    "id": {"type": "string", "pattern": "^E[0-9]+$"},
                    "source": {
                        "type": "string",
                        "enum": ["paper_repo", "run_artifact", "paper_text", "metadata"],
                    },
                    "locator": {"type": "string", "maxLength": 200},
                    "quote": {"type": "string", "maxLength": 500},
                },
            },
        },
    },
}


INSIGHTS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["run_id", "paper_id", "maturity", "signals", "blockers", "next_actions"],
    "properties": {
        "run_id": {"type": "string"},
        "paper_id": {"type": "string"},
        "maturity": {
            "type": "object",
            "additionalProperties": False,
            "required": ["level", "reason"],
            "properties": {
                "level": {
                    "type": "string",
                    "enum": [
                        "L0_NOT_RUNNABLE",
                        "L1_SMOKE",
                        "L2_TESTS",
                        "L3_PAPER_STEPS",
                        "L4_METRICS_MATCHED",
                    ],
                },
                "reason": {"type": "string", "maxLength": 500},
            },
        },
        "signals": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "source", "locator", "quote"],
                "properties": {
                    "id": {"type": "string", "pattern": "^S[0-9]+$"},
                    "source": {
                        "type": "string",
                        "enum": [
                            "summary",
                            "repo_validation",
                            "results_jsonl",
                            "bench_report",
                            "paper_to_code",
                            "metadata",
                        ],
                    },
                    "locator": {"type": "string", "maxLength": 200},
                    "quote": {"type": "string", "maxLength": 500},
                },
            },
        },
        "blockers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "description", "severity", "basis", "signal_ids"],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "auth",
                            "network_dns",
                            "missing_dependency",
                            "repo_not_found",
                            "test_failed",
                            "unknown",
                        ],
                    },
                    "description": {"type": "string", "maxLength": 400},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "basis": {
                        "type": "string",
                        "enum": ["run_log", "repo_validation", "bench_report", "summary", "inference"],
                    },
                    "signal_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                },
            },
        },
        "next_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "why", "requires", "risk", "basis", "signal_ids", "needs_approval"],
                "properties": {
                    "title": {"type": "string", "maxLength": 120},
                    "why": {"type": "string", "maxLength": 400},
                    "requires": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "allow_network",
                            "allow_package_install",
                            "allow_write_repo",
                            "credentials_needed",
                        ],
                        "properties": {
                            "allow_network": {"type": "boolean"},
                            "allow_package_install": {"type": "boolean"},
                            "allow_write_repo": {"type": "boolean"},
                            "credentials_needed": {"type": "boolean"},
                        },
                    },
                    "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                    "basis": {"type": "string", "enum": ["repo_file", "run_log", "paper_quote", "inference"]},
                    "signal_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "needs_approval": {"type": "boolean"},
                },
            },
        },
    },
}


APPLICATIONS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["run_id", "paper_id", "applications"],
    "properties": {
        "run_id": {"type": "string"},
        "paper_id": {"type": "string"},
        "applications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "domain",
                    "proposal",
                    "why_it_fits",
                    "prerequisites",
                    "risk",
                    "basis",
                    "signal_ids",
                ],
                "properties": {
                    "domain": {"type": "string", "maxLength": 80},
                    "proposal": {"type": "string", "maxLength": 300},
                    "why_it_fits": {"type": "string", "maxLength": 400},
                    "prerequisites": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
                    "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                    "basis": {"type": "string", "enum": ["inference"]},
                    "signal_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                },
            },
        },
    },
}


APPLICATIONS_LLM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["applications"],
    "properties": {"applications": APPLICATIONS_SCHEMA["properties"]["applications"]},
}


def validate_facts(payload: dict) -> tuple[bool, str]:
    try:
        Draft202012Validator(FACTS_SCHEMA).validate(payload)
    except ValidationError as exc:
        return False, str(exc)
    return True, ""


def validate_insights(payload: dict) -> tuple[bool, str]:
    try:
        Draft202012Validator(INSIGHTS_SCHEMA).validate(payload)
    except ValidationError as exc:
        return False, str(exc)
    return True, ""


def validate_applications(payload: dict) -> tuple[bool, str]:
    try:
        Draft202012Validator(APPLICATIONS_SCHEMA).validate(payload)
    except ValidationError as exc:
        return False, str(exc)
    return True, ""


def validate_applications_llm(payload: dict) -> tuple[bool, str]:
    try:
        Draft202012Validator(APPLICATIONS_LLM_SCHEMA).validate(payload)
    except ValidationError as exc:
        return False, str(exc)
    return True, ""
