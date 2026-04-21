from __future__ import annotations
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from vv_ros_llm.vv.pytest_runner import PytestRunner
from vv_ros_llm.vv.base import MethodContext
from vv_ros_llm.schemas import ExecutionResult, ExecutionStatus


_JUNIT_PASS = (
    '<?xml version="1.0"?><testsuite tests="1" failures="0" errors="0">'
    '<testcase classname="T" name="t1"/></testsuite>'
)
_JUNIT_FAIL = (
    '<?xml version="1.0"?><testsuite tests="1" failures="1">'
    '<testcase classname="T" name="t1">'
    '<failure message="boom">trace</failure></testcase></testsuite>'
)
_JUNIT_ERR = (
    '<?xml version="1.0"?><testsuite tests="1" errors="1">'
    '<testcase classname="T" name="t1">'
    '<error message="e">et</error></testcase></testsuite>'
)


def _ctx(workspace: Path):
    return MethodContext(
        task_id="T",
        candidate_idx=0,
        candidate_code="",
        entry_point="N",
        interface_spec={},
        test_oracle={},
        workspace=workspace,
    )


def _sb(exec_result: ExecutionResult):
    return SimpleNamespace(run_command=AsyncMock(return_value=exec_result))


@pytest.mark.asyncio
async def test_all_pass(tmp_path):
    (tmp_path / ".junit.xml").write_text(_JUNIT_PASS, encoding="utf-8")
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=0, stdout="", stderr=""))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert r.passed
    assert r.execution.status == "OK"
    assert r.findings == []


@pytest.mark.asyncio
async def test_collects_failure_findings(tmp_path):
    (tmp_path / ".junit.xml").write_text(_JUNIT_FAIL, encoding="utf-8")
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=1, stdout="", stderr=""))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert not r.passed
    assert any(f.get("test", "").endswith("t1") for f in r.findings)


@pytest.mark.asyncio
async def test_handles_error_element(tmp_path):
    (tmp_path / ".junit.xml").write_text(_JUNIT_ERR, encoding="utf-8")
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=1, stdout="", stderr=""))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert not r.passed
    assert len(r.findings) == 1


@pytest.mark.asyncio
async def test_missing_junit_uses_exit_code(tmp_path):
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=0, stdout="", stderr=""))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert r.passed


@pytest.mark.asyncio
async def test_junit_parse_error(tmp_path):
    (tmp_path / ".junit.xml").write_text("<not xml", encoding="utf-8")
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=0, stdout="", stderr=""))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert any("junit parse error" in str(f) for f in r.findings)


@pytest.mark.asyncio
async def test_timeout_propagates(tmp_path):
    sb = _sb(ExecutionResult(status=ExecutionStatus.TIMEOUT, exit_code=None, timed_out=True))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert r.execution.status == "TIMEOUT"
    assert not r.passed


@pytest.mark.asyncio
async def test_stdout_truncation(tmp_path):
    big = "x" * 10_000
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=0, stdout=big, stderr=big))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert len(r.execution.stdout) <= 4000
    assert len(r.execution.stderr) <= 4000


@pytest.mark.asyncio
async def test_pytest_internal_error_rc2(tmp_path):
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=2))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert r.execution.status == "CRASH" and not r.passed


@pytest.mark.asyncio
async def test_pytest_no_tests_collected_rc5(tmp_path):
    sb = _sb(ExecutionResult(status=ExecutionStatus.OK, exit_code=5))
    r = await PytestRunner(sb).run(_ctx(tmp_path))
    assert r.execution.status == "FAIL" and not r.passed
