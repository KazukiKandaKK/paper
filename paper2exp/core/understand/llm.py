from __future__ import annotations

import os
from typing import Protocol

import requests

from paper2exp.core.models import ExperimentSpec
from paper2exp.core.utils import is_truthy_env


class LLMClient(Protocol):
    def extract_spec(self, text: str, spec: ExperimentSpec) -> ExperimentSpec:
        ...


class NoopLLM:
    def extract_spec(self, text: str, spec: ExperimentSpec) -> ExperimentSpec:
        return spec


class OpenAICompatibleLLM:
    def __init__(self) -> None:
        self.endpoint = os.getenv("PAPER2EXP_LLM_ENDPOINT")
        self.api_key = os.getenv("PAPER2EXP_LLM_API_KEY")
        self.model = os.getenv("PAPER2EXP_LLM_MODEL", "gpt-4o-mini")

    def extract_spec(self, text: str, spec: ExperimentSpec) -> ExperimentSpec:
        if not self.endpoint or not self.api_key:
            return spec
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Extract experiment run commands or repo info. Reply JSON only.",
                },
                {"role": "user", "content": text[:8000]},
            ],
            "temperature": 0.0,
        }
        try:
            resp = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
        except Exception:
            return spec
        # For MVP, ignore response parsing and keep spec unchanged.
        return spec


def get_llm_client() -> LLMClient:
    if is_truthy_env("PAPER2EXP_LLM"):
        return OpenAICompatibleLLM()
    return NoopLLM()
