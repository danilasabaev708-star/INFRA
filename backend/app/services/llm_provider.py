from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


class LlmProviderError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class LlmProvider:
    base_url: str
    model: str
    api_key: str | None = None

    async def chat(self, messages: list[dict[str, str]]) -> str:
        url = self.base_url.rstrip("/") + "/v1/chat/completions"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=settings.litellm_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmProviderError(
                "Invalid LLM response: missing choices[0].message.content."
            ) from exc


def get_llm_provider() -> LlmProvider | None:
    if not settings.litellm_url:
        return None
    model = settings.litellm_model or "gpt-4o-mini"
    return LlmProvider(base_url=settings.litellm_url, model=model, api_key=settings.litellm_api_key)
