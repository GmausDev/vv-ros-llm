from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from vv_ros_llm.schemas import MethodResult


@dataclass
class MethodContext:
    """Input to a VV method."""

    task_id: str
    candidate_idx: int
    candidate_code: str
    entry_point: str
    interface_spec: dict
    test_oracle: dict
    workspace: Path
    dependencies: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)


class VVMethod(Protocol):
    method_name: str

    async def run(self, ctx: MethodContext) -> MethodResult: ...
