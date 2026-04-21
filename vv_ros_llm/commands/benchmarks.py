from __future__ import annotations
import typer
from rich.console import Console
from rich.table import Table

from vv_ros_llm.benchmarks.loader import load_jsonl, filter_by

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_cmd(
    ctx: typer.Context,
    difficulty: str | None = typer.Option(None, "--difficulty"),
    node_type: str | None = typer.Option(None, "--node-type"),
) -> None:
    settings = ctx.obj["settings"]
    tasks, errors = load_jsonl(settings.benchmarks.data_path)
    tasks = filter_by(tasks, difficulty=difficulty, node_type=node_type)
    t = Table(title=f"Benchmarks ({len(tasks)} shown, {len(errors)} skipped)")
    for col in ("task_id", "difficulty", "node_type", "entry_point"):
        t.add_column(col)
    for b in tasks:
        t.add_row(b.task_id, str(b.difficulty), b.node_type, b.entry_point)
    console.print(t)


@app.command("show")
def show_cmd(ctx: typer.Context, task_id: str = typer.Argument(...)) -> None:
    settings = ctx.obj["settings"]
    tasks, _ = load_jsonl(settings.benchmarks.data_path)
    match = next((b for b in tasks if b.task_id == task_id), None)
    if match is None:
        console.print(f"[red]Task not found:[/red] {task_id}")
        raise typer.Exit(code=2)
    console.print(match.model_dump_json(indent=2))
