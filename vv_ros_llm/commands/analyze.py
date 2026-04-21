from __future__ import annotations
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from vv_ros_llm.metrics.store import MetricsStore
from vv_ros_llm.metrics.exporter import export_runs_csv, experiment_pass_at_k

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("pass-at-k")
def pass_at_k_cmd(
    ctx: typer.Context,
    experiment_id: str = typer.Argument(...),
    k_values: str = typer.Option("", "--k"),
) -> None:
    settings = ctx.obj["settings"]
    k_list = [int(x) for x in k_values.split(",") if x.strip()] or settings.experiment.k_values
    store = MetricsStore(settings.metrics.db_path)
    out = experiment_pass_at_k(store, experiment_id, k_list)
    t = Table(title=f"pass@k for {experiment_id}")
    t.add_column("k")
    t.add_column("pass@k")
    for k in k_list:
        t.add_row(str(k), f"{out.get(k, 0.0):.4f}")
    console.print(t)
    store.close()


@app.command("export-csv")
def export_csv_cmd(
    ctx: typer.Context,
    experiment_id: str = typer.Argument(...),
    output: Path = typer.Option(Path("results/runs.csv"), "--output", "-o"),
) -> None:
    settings = ctx.obj["settings"]
    store = MetricsStore(settings.metrics.db_path)
    out = export_runs_csv(store, experiment_id, output)
    console.print(f"[green]Wrote[/green] {out}")
    store.close()
