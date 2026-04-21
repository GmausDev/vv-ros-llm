from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from typer.testing import CliRunner

from vv_ros_llm.cli import app

runner = CliRunner()


def _cfg(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "llm:\n  openai: {model: m, temperature: 0.0, max_tokens: 100}\n"
        "  anthropic: {model: m, temperature: 0.0, max_tokens: 100}\n"
        "  ollama: {model: m, temperature: 0.0, max_tokens: 100, base_url: 'http://localhost:11434'}\n"
    )
    return p


def test_docker_check_image_present(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    client = MagicMock()
    client.images.get.return_value = MagicMock()
    monkeypatch.setattr("docker.from_env", lambda: client)
    r = runner.invoke(app, ["--config", str(cfg), "docker", "check"])
    assert r.exit_code == 0


def test_docker_check_image_missing(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    from docker.errors import ImageNotFound
    client = MagicMock()
    client.images.get.side_effect = ImageNotFound("no")
    monkeypatch.setattr("docker.from_env", lambda: client)
    r = runner.invoke(app, ["--config", str(cfg), "docker", "check"])
    assert r.exit_code == 1


def test_docker_check_daemon_down(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    from docker.errors import DockerException

    def _raise_daemon():
        raise DockerException("daemon not reachable")

    monkeypatch.setattr("docker.from_env", _raise_daemon)
    r = runner.invoke(app, ["--config", str(cfg), "docker", "check"])
    assert r.exit_code == 2
