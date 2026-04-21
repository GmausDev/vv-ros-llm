from __future__ import annotations

import asyncio
import time

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    RateLimitError,
)

from .base import GenerationOutput, LLMProvider
from .retry import RetryableLLMError, llm_retry


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"

    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)

    def count_tokens(self, text: str) -> int:
        # Anthropic SDK count_tokens is async; cheap heuristic for sync use.
        return max(1, len(text) // 4)

    async def _one(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        seed: int | None,
    ) -> GenerationOutput:
        t0 = time.perf_counter()
        try:
            async for attempt in llm_retry():
                with attempt:
                    try:
                        resp = await self._client.messages.create(
                            model=self.model,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            messages=[{"role": "user", "content": prompt}],
                        )
                    except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                        raise RetryableLLMError(str(e)) from e
                    except APIStatusError as e:
                        if e.status_code and 500 <= e.status_code < 600:
                            raise RetryableLLMError(str(e)) from e
                        raise
        except Exception as e:
            return GenerationOutput(
                text="",
                raw_response=None,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=(time.perf_counter() - t0) * 1000,
                model=self.model,
                provider=self.provider_name,
                seed=seed,
                error=str(e),
            )
        text = "".join(
            block.text for block in resp.content
            if getattr(block, "type", "") == "text" and hasattr(block, "text")
        )
        usage = resp.usage
        return GenerationOutput(
            text=text,
            raw_response=text,
            prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(usage, "output_tokens", 0) or 0,
            latency_ms=(time.perf_counter() - t0) * 1000,
            model=self.model,
            provider=self.provider_name,
            seed=seed,
            error=None,
        )

    async def generate(
        self,
        prompt: str,
        n: int = 1,
        temperature: float | None = None,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> list[GenerationOutput]:
        t = self.temperature if temperature is None else temperature
        m = self.max_tokens if max_tokens is None else max_tokens
        seeds = [None if seed is None else seed + i for i in range(n)]
        return await asyncio.gather(*[self._one(prompt, t, m, s) for s in seeds])
