from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus, MethodResult
from vv_ros_llm.vv.base import MethodContext
from vv_ros_llm.vv.pipeline import VVPipeline, default_method_registry


def _ctx(tmp_path):
    return MethodContext(
        task_id="T",
        candidate_idx=0,
        candidate_code="",
        entry_point="N",
        interface_spec={},
        test_oracle={"checks": []},
        workspace=tmp_path,
    )


def _ok(name: str) -> MethodResult:
    return MethodResult(
        method=name,
        passed=True,
        execution=ExecutionResult(status=ExecutionStatus.OK),
    )


def _fail(name: str) -> MethodResult:
    return MethodResult(
        method=name,
        passed=False,
        execution=ExecutionResult(status=ExecutionStatus.FAIL),
    )


@pytest.mark.asyncio
async def test_pipeline_runs_methods_and_writes_oracle_tests(tmp_path):
    m_ruff = SimpleNamespace(method_name="ruff", run=AsyncMock(return_value=_ok("ruff")))
    m_pyt = SimpleNamespace(method_name="pytest", run=AsyncMock(return_value=_ok("pytest")))
    p = VVPipeline(
        ["ruff", "pytest"],
        sandbox=None,
        registry={"ruff": m_ruff, "pytest": m_pyt},
    )
    vr = await p.run(_ctx(tmp_path))
    assert vr.overall_pass
    assert (tmp_path / "tests" / "test_oracle.py").exists()
    assert [m.method for m in vr.methods] == ["ruff", "pytest"]


@pytest.mark.asyncio
async def test_pipeline_required_methods_gate_overall_pass(tmp_path):
    m_ruff = SimpleNamespace(method_name="ruff", run=AsyncMock(return_value=_ok("ruff")))
    m_pyt = SimpleNamespace(method_name="pytest", run=AsyncMock(return_value=_fail("pytest")))
    p = VVPipeline(
        ["ruff", "pytest"],
        sandbox=None,
        registry={"ruff": m_ruff, "pytest": m_pyt},
    )
    vr = await p.run(_ctx(tmp_path))
    assert not vr.overall_pass


@pytest.mark.asyncio
async def test_pipeline_unknown_method_is_skipped_with_warning(tmp_path, caplog):
    m_ruff = SimpleNamespace(method_name="ruff", run=AsyncMock(return_value=_ok("ruff")))
    p = VVPipeline(["ruff", "bogus"], sandbox=None, registry={"ruff": m_ruff})
    vr = await p.run(_ctx(tmp_path))
    assert [m.method for m in vr.methods] == ["ruff"]


@pytest.mark.asyncio
async def test_pipeline_catches_method_exception_as_crash(tmp_path):
    m_boom = SimpleNamespace(
        method_name="ruff", run=AsyncMock(side_effect=RuntimeError("boom"))
    )
    p = VVPipeline(
        ["ruff"],
        sandbox=None,
        registry={"ruff": m_boom},
        required_methods={"ruff"},
    )
    vr = await p.run(_ctx(tmp_path))
    assert not vr.overall_pass
    crash = vr.methods[0]
    assert crash.execution.status in (ExecutionStatus.CRASH, "CRASH")


def test_default_method_registry_keys():
    sandbox = SimpleNamespace()
    reg = default_method_registry(sandbox)
    assert set(reg.keys()) >= {"ruff", "pylint_ros", "pytest", "hypothesis", "z3"}
