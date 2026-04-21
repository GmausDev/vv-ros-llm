from __future__ import annotations

import asyncio
import json
import time

from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus, MethodResult

from .base import MethodContext


class RuffCheck:
    method_name = "ruff"

    async def run(self, ctx: MethodContext) -> MethodResult:
        node_path = ctx.workspace / "candidate_node.py"
        if not node_path.exists():
            return MethodResult(
                method="ruff",
                passed=False,
                findings=[{"error": "candidate_node.py missing"}],
                execution=ExecutionResult(
                    status=ExecutionStatus.CRASH, stderr="missing file"
                ),
            )
        t0 = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "--output-format=json",
                str(node_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await proc.communicate()
            duration_ms = (time.perf_counter() - t0) * 1000
            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")
            rc = proc.returncode
        except FileNotFoundError:
            return MethodResult(
                method="ruff",
                passed=False,
                findings=[{"error": "ruff not installed"}],
                execution=ExecutionResult(
                    status=ExecutionStatus.CRASH,
                    stderr="ruff not on PATH",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                ),
            )

        try:
            findings = json.loads(stdout) if stdout.strip() else []
        except json.JSONDecodeError:
            findings = []

        if rc == 0:
            status = ExecutionStatus.OK
            passed = True
        elif rc == 1:
            status = ExecutionStatus.FAIL
            passed = False
        else:
            status = ExecutionStatus.CRASH
            passed = False

        return MethodResult(
            method="ruff",
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
