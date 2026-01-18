from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> dict:
        ...
