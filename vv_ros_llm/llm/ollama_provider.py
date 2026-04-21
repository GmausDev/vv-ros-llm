from __future__ import annotations

import asyncio
import time

import httpx

from .base import GenerationOutput, LLMProvider
from .retry import RetryableLLMError, llm_retry


class OllamaProvider(LLMProvider):
    provider_name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    async def _one(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        seed: int | None,
    ) -> GenerationOutput:
        t0 = time.perf_counter()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **({"seed": seed} if seed is not None else {}),
            },
        }
        try:
            async def _call() -> httpx.Response:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    r = await client.post(f"{self.base_url}/api/generate", json=payload)
                    if r.status_code == 429 or 500 <= r.status_code < 600:
                        raise RetryableLLMError(
                            f"ollama status {r.status_code}: {r.text[:200]}"
                        )
                    r.raise_for_status()
                    return r

            resp: httpx.Response | None = None
            async for attempt in llm_retry():
                with attempt:
                    resp = await _call()
            assert resp is not None
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
        data = resp.json()
        text = data.get("response", "") or ""
        prompt_eval = int(data.get("prompt_eval_count", 0) or 0)
        eval_count = int(data.get("eval_count", 0) or 0)
        return GenerationOutput(
            text=text,
            raw_response=text,
            prompt_tokens=prompt_eval,
            completion_tokens=eval_count,
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
