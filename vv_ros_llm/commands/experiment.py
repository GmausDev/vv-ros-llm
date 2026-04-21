from __future__ import annotations
import asyncio
import hashlib
import json
import uuid
from pathlib import Path

import typer
from rich.console import Console

from vv_ros_llm.benchmarks.loader import load_jsonl, filter_by
from vv_ros_llm.llm.factory import build_provider
from vv_ros_llm.vv.sandbox import DockerSandbox, DockerSandboxConfig
from vv_ros_llm.vv.pipeline import VVPipeline
from vv_ros_llm.metrics.store import MetricsStore

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("run")
def run_cmd(
    ctx: typer.Context,
    provider_name: str = typer.Option("openai", "--provider", "-p"),
    n_candidates: int = typer.Option(None, "--n", help="Override config n_candidates."),
    task_ids: str = typer.Option("", "--task-ids", help="Comma-separated task IDs to include."),
    difficulty: str | None = typer.Option(None, "--difficulty"),
    node_type: str | None = typer.Option(None, "--node-type"),
    resume: bool = typer.Option(False, "--resume"),
    experiment_id: str | None = typer.Option(None, "--experiment-id"),
    results_dir: Path | None = typer.Option(None, "--results-dir"),
) -> None:
    settings = ctx.obj["settings"]
    from vv_ros_llm.experiment.runner import ExperimentRunner

    tasks, _ = load_jsonl(settings.benchmarks.data_path)
    if task_ids.strip():
        wanted = {s.strip() for s in task_ids.split(",") if s.strip()}
        tasks = [t for t in tasks if t.task_id in wanted]
    tasks = filter_by(tasks, difficulty=difficulty, node_type=node_type)
    if not tasks:
        console.print("[yellow]No benchmarks matched filters.[/yellow]")
        raise typer.Exit(code=1)

    provider = build_provider(provider_name, settings)
    sandbox_cfg = DockerSandboxConfig(
        image=settings.docker.image,
        timeout=settings.docker.timeout,
        memory_limit=settings.docker.memory_limit,
        cpus=settings.docker.cpus,
        network=settings.docker.network,
    )
    sandbox = DockerSandbox(sandbox_cfg)
    pipeline = VVPipeline(settings.vv_pipeline.enabled_methods, sandbox)

    db_path = Path(settings.metrics.db_path)
    store = MetricsStore(db_path)

    exp_id = experiment_id or f"exp-{uuid.uuid4().hex[:8]}"
    cfg_json = json.dumps(settings.model_dump(mode="json"), sort_keys=True, default=str)
    cfg_hash = hashlib.sha256(cfg_json.encode("utf-8")).hexdigest()[:12]
    store.insert_experiment(exp_id, cfg_hash, cfg_json)
    console.print(f"[green]Experiment:[/green] {exp_id} ({len(tasks)} tasks)")

    runner = ExperimentRunner(settings=settings, provider=provider, pipeline=pipeline, store=store)
    n = n_candidates if n_candidates is not None else settings.experiment.n_candidates

    try:
        asyncio.run(sandbox.ensure_image())
    except typer.Exit:
        raise
    except Exception as e:
        from vv_ros_llm.vv.sandbox import ImageMissing
        if isinstance(e, ImageMissing):
            console.print(f"[red]Docker image missing:[/red] {settings.docker.image}")
            console.print("Run: [cyan]make docker-build[/cyan]")
            raise typer.Exit(code=2)
        console.print(f"[yellow]Sandbox pre-check skipped:[/yellow] {e}")

    try:
        asyncio.run(runner.run(experiment_id=exp_id, benchmarks=tasks, n_candidates=n, resume=resume))
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted — partial results stored.[/yellow]")
    finally:
        store.finalize_experiment(exp_id)
        store.close()
        if hasattr(sandbox, "close"):
            try:
                sandbox.close()
            except Exception:
                pass


@app.command("status")
def status_cmd(ctx: typer.Context, experiment_id: str = typer.Argument(...)) -> None:
    settings = ctx.obj["settings"]
    store = MetricsStore(settings.metrics.db_path)
    rows = store.query_runs(experiment_id)
    total = len(rows)
    passed = sum(1 for r in rows if r["overall_pass"])
    console.print(f"{experiment_id}: {total} runs, {passed} passed ({(passed/max(1,total)*100):.1f}%)")
    store.close()
