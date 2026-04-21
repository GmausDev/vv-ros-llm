from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Any

from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus, MethodResult

from .base import MethodContext
from .sandbox import DockerSandbox


class PytestRunner:
    method_name = "pytest"

    def __init__(self, sandbox: DockerSandbox):
        self.sandbox = sandbox

    async def run(self, ctx: MethodContext) -> MethodResult:
        t0 = time.perf_counter()
        junit_path = "/workspace/.junit.xml"
        cmd = [
            "bash",
            "-lc",
            f"pytest -q --junitxml={junit_path} tests/",
        ]
        exec_result = await self.sandbox.run_command(cmd, workspace=ctx.workspace)
        duration_ms = (time.perf_counter() - t0) * 1000

        junit_host = ctx.workspace / ".junit.xml"
        findings: list[dict[str, Any]] = []

        # pytest exit codes:
        # 0=all passed, 1=tests failed, 2=user interrupted, 3=internal error,
        # 4=cmd line usage error, 5=no tests collected.
        rc = exec_result.exit_code
        if exec_result.status == ExecutionStatus.TIMEOUT:
            status = ExecutionStatus.TIMEOUT
            passed_all = False
        elif exec_result.status == ExecutionStatus.OOM:
            status = ExecutionStatus.OOM
            passed_all = False
        elif rc == 0:
            status = ExecutionStatus.OK
            passed_all = True
        elif rc == 1:
            status = ExecutionStatus.FAIL
            passed_all = False
        elif rc in (2, 3, 4):
            status = ExecutionStatus.CRASH
            passed_all = False
        elif rc == 5:
            status = ExecutionStatus.FAIL
            passed_all = False
        else:
            status = ExecutionStatus.CRASH
            passed_all = False

        if junit_host.exists():
            try:
                root = ET.parse(junit_host).getroot()
                for tc in root.iter("testcase"):
                    name = tc.get("name", "?")
                    classname = tc.get("classname", "")
                    failure = tc.find("failure")
                    if failure is None:
                        failure = tc.find("error")
                    if failure is not None:
                        findings.append(
                            {
                                "test": f"{classname}.{name}",
                                "message": failure.get("message", ""),
                                "text": (failure.text or "")[:1000],
                            }
                        )
            except ET.ParseError as e:
                findings.append({"error": f"junit parse error: {e}"})

        return MethodResult(
            method="pytest",
            passed=passed_all,
            score=None,
            findings=findings,
            execution=ExecutionResult(
                status=status,
                stdout=exec_result.stdout[:4000],
                stderr=exec_result.stderr[:4000],
                exit_code=exec_result.exit_code,
                duration_ms=duration_ms,
                timed_out=exec_result.timed_out,
            ),
        )
