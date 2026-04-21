from __future__ import annotations
import typer
from rich.console import Console

from vv_ros_llm import __version__
from vv_ros_llm.config import load_settings
from vv_ros_llm.logging import setup_logging

from vv_ros_llm.commands import benchmarks as benchmarks_cmd
from vv_ros_llm.commands import experiment as experiment_cmd
from vv_ros_llm.commands import analyze as analyze_cmd
from vv_ros_llm.commands import db as db_cmd
from vv_ros_llm.commands import docker as docker_cmd

app = typer.Typer(
    name="vv-ros-llm",
    help="Verification & Validation framework for LLM-generated ROS 2 code.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console()

app.add_typer(benchmarks_cmd.app, name="benchmarks", help="List and inspect ROS benchmarks.")
app.add_typer(experiment_cmd.app, name="experiment", help="Run and inspect experiments.")
app.add_typer(analyze_cmd.app, name="analyze", help="Analyze experiment results.")
app.add_typer(db_cmd.app, name="db", help="Metrics database operations.")
app.add_typer(docker_cmd.app, name="docker", help="Docker sandbox operations.")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"vv-ros-llm {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    config: str = typer.Option("config/default.yaml", "--config", "-c", help="Path to config YAML."),
    log_level: str = typer.Option("INFO", "--log-level", help="Log level."),
    version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True),
) -> None:
    """vv-ros-llm — V&V for LLM-generated ROS 2 code."""
    setup_logging(level=log_level)
    settings = load_settings(config)
    ctx.obj = {"settings": settings, "config_path": config}


if __name__ == "__main__":
    app()
