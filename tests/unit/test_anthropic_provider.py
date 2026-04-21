from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from vv_ros_llm.llm.anthropic_provider import AnthropicProvider


def _text_block(text: str):
    return SimpleNamespace(type="text", text=text)


def _tool_block():
    return SimpleNamespace(type="tool_use", text="ignored")


def _make_response(blocks, in_tok: int = 5, out_tok: int = 7):
    return SimpleNamespace(
        content=blocks,
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


@pytest.fixture
def provider():
    p = AnthropicProvider(model="claude-x", api_key="fake", temperature=0.2, max_tokens=50)
    p._client = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock()))
    return p


def test_count_tokens_heuristic(provider):
    assert provider.count_tokens("") == 1
    assert provider.count_tokens("abcd") == 1
    assert provider.count_tokens("a" * 40) == 10


@pytest.mark.asyncio
async def test_generate_concatenates_text_blocks_ignoring_tool_use(provider):
    provider._client.messages.create = AsyncMock(
        return_value=_make_response(
            [_text_block("hi "), _tool_block(), _text_block("there")], 2, 3
        )
    )
    out = await provider.generate(prompt="p", n=1)
    assert out[0].text == "hi there"
    assert out[0].prompt_tokens == 2 and out[0].completion_tokens == 3
    assert out[0].provider == "anthropic"


@pytest.mark.asyncio
async def test_generate_retries_on_timeout(provider):
    try:
        from anthropic import APITimeoutError

        te = APITimeoutError(request=SimpleNamespace())
    except Exception:
        pytest.skip("APITimeoutError constructor incompatible with test stub")
    provider._client.messages.create = AsyncMock(
        side_effect=[te, _make_response([_text_block("ok")], 1, 1)]
    )
    out = await provider.generate(prompt="p", n=1)
    assert out[0].error is None
    assert provider._client.messages.create.await_count == 2


@pytest.mark.asyncio
async def test_generate_returns_error_on_non_retryable_status(provider):
    try:
        from anthropic import APIStatusError

        err = APIStatusError(
            "bad",
            response=SimpleNamespace(status_code=400, headers={}, request=None),
            body=None,
        )
    except Exception:
        pytest.skip("APIStatusError constructor incompatible with test stub")
    provider._client.messages.create = AsyncMock(side_effect=err)
    out = await provider.generate(prompt="p", n=1)
    assert out[0].error is not None and out[0].text == ""


@pytest.mark.asyncio
async def test_generate_n_seeds_increment(provider):
    provider._client.messages.create = AsyncMock(
        return_value=_make_response([_text_block("r")], 1, 1)
    )
    outs = await provider.generate(prompt="p", n=3, seed=100)
    assert [o.seed for o in outs] == [100, 101, 102]
