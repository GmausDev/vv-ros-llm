from __future__ import annotations
import subprocess

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("build")
def build_cmd(ctx: typer.Context) -> None:
    """Build the vv-ros-executor:humble sandbox image."""
    settings = ctx.obj["settings"]
    image = settings.docker.image
    cmd = ["docker", "build", "-t", image, "-f", "docker/Dockerfile", "."]
    console.print(f"[cyan]$[/cyan] {' '.join(cmd)}")
    rc = subprocess.call(cmd)
    raise typer.Exit(code=rc)


@app.command("check")
def check_cmd(ctx: typer.Context) -> None:
    """Verify that the sandbox image exists locally."""
    settings = ctx.obj["settings"]
    import docker as docker_sdk
    from docker.errors import DockerException, ImageNotFound
    try:
        client = docker_sdk.from_env()
        client.images.get(settings.docker.image)
        console.print(f"[green]OK[/green] image {settings.docker.image} present")
    except ImageNotFound:
        console.print(f"[red]MISSING[/red] image {settings.docker.image}")
        console.print("Run: [cyan]make docker-build[/cyan]")
        raise typer.Exit(code=1)
    except DockerException as e:
        console.print("[red]Docker daemon not reachable.[/red] Is Docker running?")
        console.print(f"[dim]{e}[/dim]")
        raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=3)
