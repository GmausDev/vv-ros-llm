"""End-to-end smoke test: CLI runs with all externals stubbed (<5s)."""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from vv_ros_llm.cli import app

runner = CliRunner()


def test_cli_help_returns_zero():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "vv-ros-llm" in r.output.lower() or "Usage" in r.output


def test_cli_version_returns_zero():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert "vv-ros-llm" in r.output.lower()


def test_db_init_creates_sqlite(tmp_path: Path, monkeypatch):
    db = tmp_path / "metrics.db"
    monkeypatch.setenv("VV_ROS_LLM_METRICS__DB_PATH", str(db))
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "llm:\n  openai: {model: m, temperature: 0.0, max_tokens: 100}\n"
        "  anthropic: {model: m, temperature: 0.0, max_tokens: 100}\n"
        "  ollama: {model: m, temperature: 0.0, max_tokens: 100,"
        " base_url: 'http://localhost:11434'}\n"
        f"metrics:\n  db_path: {db}\n"
    )
    r = runner.invoke(app, ["--config", str(cfg), "db", "init"])
    assert r.exit_code == 0, r.output
    assert db.exists()


def test_benchmarks_list_parses_fixture(tmp_path: Path, sample_benchmarks_path: Path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "llm:\n  openai: {model: m, temperature: 0.0, max_tokens: 100}\n"
        "  anthropic: {model: m, temperature: 0.0, max_tokens: 100}\n"
        "  ollama: {model: m, temperature: 0.0, max_tokens: 100, base_url: 'http://localhost:11434'}\n"
        f"benchmarks:\n  data_path: {sample_benchmarks_path}\n"
    )
    r = runner.invoke(app, ["--config", str(cfg), "benchmarks", "list"])
    assert r.exit_code == 0, r.output
    assert "SAMPLE-0" in r.output or "SAMPLE-1" in r.output
