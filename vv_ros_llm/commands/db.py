from __future__ import annotations
from pathlib import Path

import typer
from rich.console import Console

from vv_ros_llm.metrics.store import MetricsStore

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("init")
def init_cmd(ctx: typer.Context) -> None:
    settings = ctx.obj["settings"]
    store = MetricsStore(settings.metrics.db_path)
    console.print(f"[green]Initialized[/green] {settings.metrics.db_path}")
    store.close()


@app.command("path")
def path_cmd(ctx: typer.Context) -> None:
    settings = ctx.obj["settings"]
    console.print(str(Path(settings.metrics.db_path).resolve()))
