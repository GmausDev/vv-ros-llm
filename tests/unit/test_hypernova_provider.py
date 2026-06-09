from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml
from openai import NOT_GIVEN

from vv_ros_llm.config import load_settings
from vv_ros_llm.llm.factory import build_provider
from vv_ros_llm.llm.hypernova_provider import COMPACTIFAI_BASE_URL, HypernovaProvider


def _make_completion(text: str, p_tok: int = 5, c_tok: int = 7):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=p_tok, completion_tokens=c_tok),
    )


@pytest.fixture
def provider():
    p = HypernovaProvider(
        model="hypernova-60b", api_key="fake", temperature=0.2, max_tokens=50
    )
    p._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock()))
    )
    return p


@pytest.fixture
def sample_yaml(tmp_path: Path) -> Path:
    data = {
        "llm": {
            "openai": {"model": "gpt-4o", "temperature": 0.5, "max_tokens": 4000},
            "anthropic": {"model": "claude", "temperature": 0.4, "max_tokens": 4000},
            "ollama": {"model": "llama3", "temperature": 0.7, "max_tokens": 4000,
                       "base_url": "http://localhost:11434"},
            "hypernova": {"model": "hypernova-60b", "temperature": 0.6,
                          "max_tokens": 2048,
                          "base_url": "https://api.compactif.ai/v1"},
        },
        "docker": {"image": "img:tag", "timeout": 30, "memory_limit": "2g",
                   "cpus": 1.0, "network": "none"},
    }
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(data))
    return p


def test_provider_name_and_default_base_url():
    p = HypernovaProvider(model="hypernova-60b", api_key="fake")
    assert p.provider_name == "hypernova"
    assert str(p._client.base_url).rstrip("/") == COMPACTIFAI_BASE_URL.rstrip("/")


@pytest.mark.asyncio
async def test_generate_parses_completion_and_tokens(provider):
    provider._client.chat.completions.create = AsyncMock(
        return_value=_make_completion("```python\nx=1\n```", 3, 4)
    )
    out = await provider.generate(prompt="p", n=1)
    assert len(out) == 1
    g = out[0]
    assert g.provider == "hypernova" and g.model == "hypernova-60b"
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
async def test_generate_retries_on_5xx(provider):
    try:
        from openai import APIStatusError

        err = APIStatusError(
            "upstream sad",
            response=SimpleNamespace(status_code=503, headers={}, request=None),
            body=None,
        )
    except Exception:
        pytest.skip("APIStatusError constructor incompatible with test stub")
    provider._client.chat.completions.create = AsyncMock(
        side_effect=[err, _make_completion("ok", 1, 1)]
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
async def test_generate_never_sends_seed_and_records_none(provider):
    provider._client.chat.completions.create = AsyncMock(
        return_value=_make_completion("r", 1, 1)
    )
    out = await provider.generate(prompt="p", n=3, seed=42)
    calls = provider._client.chat.completions.create.await_args_list
    assert len(calls) == 3
    assert all(c.kwargs["seed"] is NOT_GIVEN for c in calls)
    assert all(g.seed is None for g in out)


def test_build_provider_hypernova_from_settings(sample_yaml: Path, monkeypatch):
    monkeypatch.setenv("HYPERNOVA_API_KEY", "hn-key")
    s = load_settings(sample_yaml)
    p = build_provider("hypernova", s)
    assert isinstance(p, HypernovaProvider)
    assert p.model == "hypernova-60b"
    assert p.temperature == 0.6 and p.max_tokens == 2048
    assert str(p._client.base_url).rstrip("/") == "https://api.compactif.ai/v1"
    assert p._client.api_key == "hn-key"


def test_build_provider_unknown_name_raises(sample_yaml: Path):
    s = load_settings(sample_yaml)
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_provider("grok", s)
