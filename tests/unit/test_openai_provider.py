from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from vv_ros_llm.llm.openai_provider import OpenAIProvider


def _make_completion(text: str, p_tok: int = 5, c_tok: int = 7):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=p_tok, completion_tokens=c_tok),
    )


@pytest.fixture
def provider():
    p = OpenAIProvider(model="gpt-4o-mini", api_key="fake", temperature=0.2, max_tokens=50)
    p._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock()))
    )
    return p


def test_count_tokens_with_tiktoken(provider):
    n = provider.count_tokens("hello world")
    assert n >= 1


def test_count_tokens_fallback_when_tiktoken_missing(monkeypatch):
    monkeypatch.setattr("vv_ros_llm.llm.openai_provider.tiktoken", None)
    p = OpenAIProvider(model="x", api_key="fake")
    assert p.count_tokens("abcd efgh") >= 1


@pytest.mark.asyncio
async def test_generate_parses_completion_and_tokens(provider):
    provider._client.chat.completions.create = AsyncMock(
        return_value=_make_completion("```python\nx=1\n```", 3, 4)
    )
    out = await provider.generate(prompt="p", n=1)
    assert len(out) == 1
    g = out[0]
    assert g.provider == "openai" and g.model == "gpt-4o-mini"
    assert "x=1" in g.text
    assert g.prompt_tokens == 3 and g.completion_tokens == 4
    assert g.error is None and g.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_generate_retries_on_rate_limit(provider):
    try:
        from openai import RateLimitError

        rle = RateLimitError(
            "slow down",
            response=SimpleNamespace(status_code=429, headers={}, request=None),
            body=None,
        )
    except Exception:
        pytest.skip("RateLimitError constructor incompatible with test stub")
    provider._client.chat.completions.create = AsyncMock(
        side_effect=[rle, _make_completion("ok", 1, 1)]
    )
    out = await provider.generate(prompt="p", n=1)
    assert out[0].error is None
    assert provider._client.chat.completions.create.await_count == 2


@pytest.mark.asyncio
async def test_generate_returns_error_on_non_retryable_4xx(provider):
    try:
        from openai import APIStatusError

        err = APIStatusError(
            "bad",
            response=SimpleNamespace(status_code=400, headers={}, request=None),
            body=None,
        )
    except Exception:
        pytest.skip("APIStatusError constructor incompatible with test stub")
    provider._client.chat.completions.create = AsyncMock(side_effect=err)
    out = await provider.generate(prompt="p", n=1)
    assert out[0].error is not None and out[0].text == ""


@pytest.mark.asyncio
async def test_generate_n_seeds_increment(provider):
    provider._client.chat.completions.create = AsyncMock(
        return_value=_make_completion("r", 1, 1)
    )
    await provider.generate(prompt="p", n=3, seed=10)
    calls = provider._client.chat.completions.create.await_args_list
    seeds = [c.kwargs["seed"] for c in calls]
    assert seeds == [10, 11, 12]
