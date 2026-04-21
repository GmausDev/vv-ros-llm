from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import docker
from docker.errors import APIError, ImageNotFound
from docker.models.containers import Container

from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus

log = logging.getLogger(__name__)


@dataclass
class DockerSandboxConfig:
    image: str = "vv-ros-executor:humble"
    timeout: int = 120
    memory_limit: str = "4g"
    cpus: float = 2.0
    network: str = "none"
    workdir: str = "/workspace"
    label: str = "vv-ros-llm=1"


class ImageMissing(RuntimeError):
    """Raised when the sandbox image is not built."""


class DockerSandbox:
    """Wraps docker-py (sync) with asyncio.to_thread for use in async pipeline."""

    def __init__(self, cfg: DockerSandboxConfig | None = None):
        self.cfg = cfg or DockerSandboxConfig()
        self._client = docker.from_env()

    async def ensure_image(self) -> None:
        try:
            await asyncio.to_thread(self._client.images.get, self.cfg.image)
        except ImageNotFound as e:
            raise ImageMissing(
                f"Docker image {self.cfg.image!r} not found. Run `make docker-build` first."
            ) from e

    async def run_command(
        self,
        cmd: list[str] | str,
        workspace: Path,
        env: dict[str, str] | None = None,
        extra_binds: dict[str, dict] | None = None,
    ) -> ExecutionResult:
        """Run `cmd` inside a fresh container bound to `workspace`; return ExecutionResult."""
        t0 = time.perf_counter()
        volumes: dict[str, dict] = {
            str(workspace.resolve()): {"bind": self.cfg.workdir, "mode": "rw"},
        }
        if extra_binds:
            volumes.update(extra_binds)
        try:
            container: Container = await asyncio.shield(asyncio.to_thread(
                self._client.containers.run,
                image=self.cfg.image,
                command=cmd,
                detach=True,
                remove=False,
                network_mode=self.cfg.network,
                mem_limit=self.cfg.memory_limit,
                nano_cpus=int(self.cfg.cpus * 1_000_000_000),
                volumes=volumes,
                working_dir=self.cfg.workdir,
                environment=env or {},
                labels={"vv-ros-llm": "1"},
            ))
        except ImageNotFound as e:
            raise ImageMissing(str(e)) from e
        except APIError as e:
            return ExecutionResult(
                status=ExecutionStatus.CRASH,
                stderr=f"docker API error: {e}",
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        try:
            try:
                result = await asyncio.to_thread(container.wait, timeout=self.cfg.timeout)
                exit_code = int(result.get("StatusCode", -1))
                timed_out = False
            except asyncio.CancelledError:
                try:
                    await asyncio.to_thread(container.kill)
                except Exception:
                    pass
                try:
                    await asyncio.to_thread(container.remove, force=True)
                except Exception:
                    pass
                raise
            except Exception:
                try:
                    await asyncio.to_thread(container.kill)
                except Exception:
                    pass
                exit_code = None
                timed_out = True

            stdout_bytes = await asyncio.to_thread(
                container.logs, stdout=True, stderr=False, tail="all"
            )
            stderr_bytes = await asyncio.to_thread(
                container.logs, stdout=False, stderr=True, tail="all"
            )
            if len(stdout_bytes) > 2_000_000:
                stdout_bytes = stdout_bytes[-2_000_000:]
            if len(stderr_bytes) > 2_000_000:
                stderr_bytes = stderr_bytes[-2_000_000:]
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            if timed_out:
                status = ExecutionStatus.TIMEOUT
            elif exit_code == 137:
                status = ExecutionStatus.OOM
            elif exit_code == 0:
                status = ExecutionStatus.OK
            else:
                status = ExecutionStatus.FAIL
            return ExecutionResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_ms=(time.perf_counter() - t0) * 1000,
                timed_out=timed_out,
            )
        finally:
            try:
                await asyncio.to_thread(container.remove, force=True)
            except Exception:
                log.exception("sandbox container remove failed")

    async def reap_leftover(self) -> int:
        """Kill+remove any orphan containers with our label. Returns count reaped."""
        try:
            containers = await asyncio.to_thread(
                self._client.containers.list,
                filters={"label": "vv-ros-llm=1"},
                all=True,
            )
        except Exception:
            return 0
        n = 0
        for c in containers:
            try:
                await asyncio.to_thread(c.remove, force=True)
                n += 1
            except Exception:
                pass
        return n

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
