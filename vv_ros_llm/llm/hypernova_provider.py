from __future__ import annotations

import asyncio

from .base import GenerationOutput
from .openai_provider import OpenAIProvider

COMPACTIFAI_BASE_URL = "https://api.compactif.ai/v1"


class HypernovaProvider(OpenAIProvider):
    """Multiverse Computing HyperNova via the OpenAI-compatible CompactifAI API."""

    provider_name = "hypernova"

    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        base_url: str | None = None,
        timeout: float = 60.0,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=base_url or COMPACTIFAI_BASE_URL,
            timeout=timeout,
        )

    async def generate(
        self,
        prompt: str,
        n: int = 1,
        temperature: float | None = None,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> list[GenerationOutput]:
        # CompactifAI silently ignores `seed`, so we never send it and record
        # seed=None — diversity is driven by temperature, like Anthropic.
        t = self.temperature if temperature is None else temperature
        m = self.max_tokens if max_tokens is None else max_tokens
        return await asyncio.gather(*[self._one(prompt, t, m, None) for _ in range(n)])
