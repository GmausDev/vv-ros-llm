from __future__ import annotations

import asyncio
import json
import time

from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus, MethodResult

from .base import MethodContext

PLUGIN_MODULE = "vv_ros_llm.vv.pylint_ros_plugin"


class PylintRosCheck:
    method_name = "pylint_ros"

    async def run(self, ctx: MethodContext) -> MethodResult:
        node_path = ctx.workspace / "candidate_node.py"
        if not node_path.exists():
            return MethodResult(
                method="pylint_ros",
                passed=False,
                findings=[{"error": "candidate_node.py missing"}],
                execution=ExecutionResult(
                    status=ExecutionStatus.CRASH, stderr="missing file"
                ),
            )
        t0 = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                "pylint",
                "--output-format=json",
                f"--load-plugins={PLUGIN_MODULE}",
                "--disable=all",
                "--enable=missing-rclpy-init,missing-rclpy-shutdown,missing-destroy-node,blocking-in-callback,missing-qos-depth",
                str(node_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await proc.communicate()
            rc = proc.returncode
            duration_ms = (time.perf_counter() - t0) * 1000
        except FileNotFoundError:
            return MethodResult(
                method="pylint_ros",
                passed=False,
                findings=[{"error": "pylint not installed"}],
                execution=ExecutionResult(
                    status=ExecutionStatus.CRASH,
                    stderr="pylint not on PATH",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                ),
            )

        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        try:
            findings = json.loads(stdout) if stdout.strip() else []
        except json.JSONDecodeError:
            findings = []

        if rc is None:
            status, passed = ExecutionStatus.CRASH, False
        elif rc == 0:
            status, passed = ExecutionStatus.OK, True
        elif rc & 32:
            status, passed = ExecutionStatus.CRASH, False
        else:
            status, passed = ExecutionStatus.FAIL, False

        return MethodResult(
            method="pylint_ros",
            passed=passed,
            score=None,
            findings=findings,
            execution=ExecutionResult(
                status=status,
                stdout=stdout[:4000],
                stderr=stderr[:4000],
                exit_code=rc,
                duration_ms=duration_ms,
            ),
        )
