from __future__ import annotations

import logging
from typing import Literal, Mapping, cast

from vv_ros_llm.schemas import (
    ExecutionResult,
    ExecutionStatus,
    MethodResult,
    VerificationResult,
)

from .base import MethodContext, VVMethod
from .hypothesis_runner import HypothesisRunner
from .oracle_runner import write_oracle_tests
from .pylint_ros import PylintRosCheck
from .pytest_runner import PytestRunner
from .ruff_check import RuffCheck
from .sandbox import DockerSandbox
from .z3_checks import Z3Checks

log = logging.getLogger(__name__)


def default_method_registry(sandbox: DockerSandbox) -> Mapping[str, VVMethod]:
    return {
        "ruff": RuffCheck(),
        "pylint_ros": PylintRosCheck(),
        "pytest": PytestRunner(sandbox),
        "hypothesis": HypothesisRunner(),
        "z3": Z3Checks(),
    }


class VVPipeline:
    def __init__(
        self,
        enabled_methods: list[str],
        sandbox: DockerSandbox,
        registry: Mapping[str, VVMethod] | None = None,
        required_methods: set[str] | None = None,
    ):
        reg = registry or default_method_registry(sandbox)
        missing = [m for m in enabled_methods if m not in reg]
        if missing:
            log.warning("Unknown VV methods (skipped): %s", missing)
        self.methods = [reg[m] for m in enabled_methods if m in reg]
        self.required = required_methods or {"ruff", "pytest"}

    async def run(self, ctx: MethodContext) -> VerificationResult:
        try:
            write_oracle_tests(ctx.workspace)
        except Exception as e:
            log.exception("Failed to write oracle tests: %s", e)
            return VerificationResult(
                task_id=ctx.task_id,
                candidate_idx=ctx.candidate_idx,
                methods=[
                    MethodResult(
                        method="pytest",
                        passed=False,
                        findings=[{"error": f"oracle_setup failed: {e}"}],
                        execution=ExecutionResult(
                            status=ExecutionStatus.CRASH, stderr=str(e)
                        ),
                    )
                ],
                overall_pass=False,
            )
        results: list[MethodResult] = []
        for method in self.methods:
            try:
                res = await method.run(ctx)
            except Exception as e:
                res = MethodResult(
                    method=cast(
                        Literal["ruff", "pylint_ros", "pytest", "hypothesis", "z3"],
                        method.method_name,
                    ),
                    passed=False,
                    findings=[{"error": f"method crashed: {e}"}],
                    execution=ExecutionResult(
                        status=ExecutionStatus.CRASH, stderr=str(e)
                    ),
                )
            results.append(res)
        required_results = [r for r in results if r.method in self.required]
        overall_pass = bool(required_results) and all(
            r.passed for r in required_results
        )
        return VerificationResult(
            task_id=ctx.task_id,
            candidate_idx=ctx.candidate_idx,
            methods=results,
            overall_pass=overall_pass,
        )
