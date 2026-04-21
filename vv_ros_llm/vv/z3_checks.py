from __future__ import annotations

import time
from typing import Any

from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus, MethodResult

from .base import MethodContext


class Z3Checks:
    """MVP: validate interface_spec invariants without invoking a solver.

    Future: encode QoS/timing constraints in z3 and prove topic graph consistency.
    """

    method_name = "z3"

    async def run(self, ctx: MethodContext) -> MethodResult:
        t0 = time.perf_counter()
        findings: list[dict[str, Any]] = []
        iface = ctx.interface_spec or {}

        pub_names = [
            t.get("name")
            for t in iface.get("topics_published", [])
            if isinstance(t, dict)
        ]
        if len(set(pub_names)) != len(pub_names):
            findings.append({"violation": "duplicate_publisher_topic"})

        for group in ("topics_published", "topics_subscribed"):
            for t in iface.get(group, []):
                if not isinstance(t, dict):
                    continue
                qos = t.get("qos")
                depth = qos.get("depth") if isinstance(qos, dict) else None
                if depth is not None and depth < 1:
                    findings.append(
                        {"violation": "qos_depth_lt_1", "topic": t.get("name")}
                    )

        passed = not findings
        status = ExecutionStatus.OK if passed else ExecutionStatus.FAIL
        return MethodResult(
            method="z3",
            passed=passed,
            score=None,
            findings=findings,
            execution=ExecutionResult(
                status=status,
                duration_ms=(time.perf_counter() - t0) * 1000,
            ),
        )
