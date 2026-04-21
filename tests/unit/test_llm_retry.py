from __future__ import annotations
import pytest
import httpx
import respx
from vv_ros_llm.llm.ollama_provider import OllamaProvider

@pytest.mark.asyncio
@respx.mock
async def test_ollama_429_retries_then_succeeds():
    route = respx.post("http://localhost:11434/api/generate").mock(
        side_effect=[
            httpx.Response(429, text="slow down"),
            httpx.Response(200, json={"response": "```python\nx=1\n```",
                                        "prompt_eval_count": 5, "eval_count": 3}),
        ]
    )
    provider = OllamaProvider(model="m", base_url="http://localhost:11434")
    results = await provider.generate(prompt="p", n=1)
    assert route.call_count >= 2
    assert results[0].text.startswith("```python") and results[0].error is None

@pytest.mark.asyncio
@respx.mock
async def test_ollama_gives_up_after_max_retries():
    route = respx.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(500, text="boom")
    )
    provider = OllamaProvider(model="m", base_url="http://localhost:11434")
    results = await provider.generate(prompt="p", n=1)
    assert results[0].error is not None
    assert route.call_count >= 1
