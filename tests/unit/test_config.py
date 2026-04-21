from __future__ import annotations
from pathlib import Path
import yaml
import pytest
from vv_ros_llm.config import load_settings

@pytest.fixture
def sample_yaml(tmp_path: Path) -> Path:
    data = {
        "llm": {
            "openai": {"model": "gpt-4o", "temperature": 0.5, "max_tokens": 4000},
            "anthropic": {"model": "claude", "temperature": 0.4, "max_tokens": 4000},
            "ollama": {"model": "llama3", "temperature": 0.7, "max_tokens": 4000,
                        "base_url": "http://localhost:11434"},
        },
        "docker": {"image": "img:tag", "timeout": 30, "memory_limit": "2g", "cpus": 1.0, "network": "none"},
    }
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(data))
    return p

def test_load_settings_reads_yaml(sample_yaml: Path):
    s = load_settings(sample_yaml)
    assert s.docker.image == "img:tag"
    assert s.docker.timeout == 30
    assert s.llm.openai.model == "gpt-4o"

def test_secret_str_redacts(sample_yaml: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-abc123")
    s = load_settings(sample_yaml)
    assert "super-secret" not in repr(s)
    assert s.openai_api_key.get_secret_value() == "sk-super-secret-abc123"

def test_env_override_nested(sample_yaml: Path, monkeypatch):
    monkeypatch.setenv("VV_ROS_LLM_DOCKER__TIMEOUT", "77")
    s = load_settings(sample_yaml)
    assert s.docker.timeout == 77

def test_env_overrides_but_yaml_fills_siblings(sample_yaml: Path, monkeypatch):
    monkeypatch.setenv("VV_ROS_LLM_DOCKER__TIMEOUT", "77")
    s = load_settings(sample_yaml)
    assert s.docker.timeout == 77
    assert s.docker.image == "img:tag"
    assert s.docker.memory_limit == "2g"

def test_env_api_key_wins_over_yaml(sample_yaml: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    s = load_settings(sample_yaml)
    assert s.openai_api_key.get_secret_value() == "env-key"

def test_missing_explicit_yaml_path_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("VV_ROS_LLM_LLM__OPENAI__MODEL", "env-model")
    monkeypatch.setenv("VV_ROS_LLM_LLM__ANTHROPIC__MODEL", "env-a")
    monkeypatch.setenv("VV_ROS_LLM_LLM__OLLAMA__MODEL", "env-o")
    monkeypatch.setenv("VV_ROS_LLM_LLM__OLLAMA__BASE_URL", "http://localhost:11434")
    import pytest
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "nonexistent.yaml")

def test_defaults_when_yaml_partial_and_env_absent(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "llm:\n"
        "  openai: {model: a, temperature: 0.0, max_tokens: 100}\n"
        "  anthropic: {model: a, temperature: 0.0, max_tokens: 100}\n"
        "  ollama: {model: a, temperature: 0.0, max_tokens: 100, base_url: 'http://x'}\n"
    )
    s = load_settings(p)
    assert s.docker.timeout == 120
    assert s.experiment.n_candidates == 5

def test_nested_list_override_via_env(sample_yaml: Path, monkeypatch):
    monkeypatch.setenv("VV_ROS_LLM_VV_PIPELINE__ENABLED_METHODS", '["ruff"]')
    s = load_settings(sample_yaml)
    assert s.vv_pipeline.enabled_methods == ["ruff"]
