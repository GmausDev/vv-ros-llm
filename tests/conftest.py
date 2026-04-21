"""Shared pytest fixtures for vv-ros-llm."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory pre-seeded for test data."""
    return tmp_path


@pytest.fixture
def sample_benchmarks_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_benchmarks.jsonl"


@pytest.fixture
def canned_llm_response() -> str:
    return (Path(__file__).parent / "fixtures" / "canned_response.txt").read_text(encoding="utf-8")


@pytest.fixture
def in_memory_store():
    from vv_ros_llm.metrics.store import MetricsStore

    s = MetricsStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def tmp_results_dir(tmp_path: Path) -> Path:
    d = tmp_path / "results"
    d.mkdir()
    return d


@pytest.fixture
def mock_docker(monkeypatch):
    """Patch docker.from_env() so DockerSandbox doesn't need a real daemon."""
    client = MagicMock()
    container = MagicMock()
    container.wait.return_value = {"StatusCode": 0}
    container.logs.side_effect = [b"stub stdout\n", b""]
    client.containers.run.return_value = container
    client.images.get.return_value = MagicMock()
    monkeypatch.setattr("docker.from_env", lambda: client)
    return client


@pytest.fixture
def stub_llm_response(canned_llm_response: str):
    """Stub LLMProvider.generate to return canned text."""
    from vv_ros_llm.llm.base import GenerationOutput

    def _make(n: int = 1, provider: str = "stub", model: str = "stub-1"):
        return [
            GenerationOutput(
                text=canned_llm_response,
                raw_response=canned_llm_response,
                prompt_tokens=10,
                completion_tokens=20,
                latency_ms=1.0,
                model=model,
                provider=provider,
                seed=None,
            )
            for _ in range(n)
        ]

    return _make
