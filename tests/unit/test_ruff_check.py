from __future__ import annotations
import json
import pytest
from vv_ros_llm.vv.ruff_check import RuffCheck
from vv_ros_llm.vv.base import MethodContext

class _FakeProc:
    def __init__(self, rc: int, stdout: bytes, stderr: bytes = b""):
        self.returncode = rc
        self._stdout = stdout
        self._stderr = stderr
    async def communicate(self):
        return self._stdout, self._stderr

@pytest.mark.asyncio
async def test_ruff_ok_when_no_findings(monkeypatch, tmp_path):
    node = tmp_path / "candidate_node.py"
    node.write_text("x = 1\n")
    async def fake_exec(*args, **kw):
        return _FakeProc(0, b"[]", b"")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="x=1", entry_point="N",
                        interface_spec={}, test_oracle={}, workspace=tmp_path)
    res = await RuffCheck().run(ctx)
    assert res.passed and res.execution.status == "OK"

@pytest.mark.asyncio
async def test_ruff_fail_on_findings(monkeypatch, tmp_path):
    (tmp_path / "candidate_node.py").write_text("x = 1\n")
    findings = [{"code": "E501", "message": "too long"}]
    async def fake_exec(*args, **kw):
        return _FakeProc(1, json.dumps(findings).encode(), b"")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="x=1", entry_point="N",
                        interface_spec={}, test_oracle={}, workspace=tmp_path)
    res = await RuffCheck().run(ctx)
    assert not res.passed and res.execution.status == "FAIL" and res.findings == findings

@pytest.mark.asyncio
async def test_ruff_crash_when_binary_missing(monkeypatch, tmp_path):
    (tmp_path / "candidate_node.py").write_text("x = 1\n")
    async def fake_exec(*args, **kw):
        raise FileNotFoundError()
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="x=1", entry_point="N",
                        interface_spec={}, test_oracle={}, workspace=tmp_path)
    res = await RuffCheck().run(ctx)
    assert res.execution.status == "CRASH"
