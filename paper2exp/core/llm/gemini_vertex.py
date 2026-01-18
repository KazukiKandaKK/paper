from __future__ import annotations

import json
import time
from typing import Any

from google import genai
from google.genai.types import HttpOptions

from paper2exp.core.llm.base import LLMClient


class GeminiVertexClient(LLMClient):
    def __init__(self, max_retries: int = 3, timeout_sec: int = 60) -> None:
        self.max_retries = max_retries
        self.timeout_sec = timeout_sec
        self.client = _build_client(timeout_sec)

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str,
        temperature: float = 0.0,
        seed: int | None = None,
    ) -> dict:
        schema = _sanitize_schema(schema)
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                        "temperature": temperature,
                    },
                )
                text = response.text or "{}"
                return json.loads(text)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(2**attempt)
        raise RuntimeError("Gemini call failed") from last_error


def _build_client(timeout_sec: int) -> genai.Client:
    try:
        timeout_ms = int(timeout_sec * 1000)
        return genai.Client(http_options=HttpOptions(api_version="v1", timeout=timeout_ms))
    except TypeError:
        return genai.Client(http_options=HttpOptions(api_version="v1"))


def _sanitize_schema(schema: dict) -> dict:
    if not isinstance(schema, dict):
        return schema
    cleaned = dict(schema)
    cleaned.pop("$schema", None)
    return cleaned
