from __future__ import annotations

import time
from typing import Any

from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus, MethodResult

from .base import MethodContext

_PRIMITIVE_MSG_STRATEGIES = {
    "std_msgs/Int32": "st.integers(min_value=-(2**31), max_value=2**31 - 1)",
    "std_msgs/Float64": "st.floats(allow_nan=False, allow_infinity=False)",
    "std_msgs/String": "st.text(max_size=64)",
    "std_msgs/Bool": "st.booleans()",
}


class HypothesisRunner:
    """MVP: host-side property test of interface_spec consistency only.

    Later iterations can fuzz published messages and assert node survives
    using a dockerized harness. For MVP we validate:
      - topic names unique across published/subscribed
      - record which published topic types are not in our primitive set
    """

    method_name = "hypothesis"

    async def run(self, ctx: MethodContext) -> MethodResult:
        t0 = time.perf_counter()
        findings: list[dict[str, Any]] = []
        iface = ctx.interface_spec or {}

        names: list[str] = []
        for group in ("topics_published", "topics_subscribed"):
            for t in iface.get(group, []):
                if isinstance(t, dict):
                    n = t.get("name")
                    if n:
                        names.append(n)
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            findings.append({"error": "duplicate topic names", "names": dupes})

        unknown: list[str] = []
        for t in iface.get("topics_published", []):
            if isinstance(t, dict):
                mt = t.get("type", "")
                if mt and mt not in _PRIMITIVE_MSG_STRATEGIES:
                    unknown.append(mt)

        passed = not findings
        status = ExecutionStatus.OK if passed else ExecutionStatus.FAIL
        extra: list[dict[str, Any]] = []
        if unknown:
            extra.append(
                {"info": "unsupported_msg_types_for_mvp", "types": sorted(set(unknown))}
            )

        return MethodResult(
            method="hypothesis",
            passed=passed,
            score=None,
            findings=findings + extra,
            execution=ExecutionResult(
                status=status,
                duration_ms=(time.perf_counter() - t0) * 1000,
            ),
        )
