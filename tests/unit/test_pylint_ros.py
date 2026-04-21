from __future__ import annotations
import json
import pytest
from vv_ros_llm.vv.pylint_ros import PylintRosCheck
from vv_ros_llm.vv.base import MethodContext

class _FakeProc:
    def __init__(self, rc, stdout=b"", stderr=b""):
        self.returncode = rc
        self._out = stdout
        self._err = stderr
    async def communicate(self):
        return self._out, self._err

@pytest.mark.asyncio
async def test_pylint_ok(monkeypatch, tmp_path):
    (tmp_path / "candidate_node.py").write_text("x=1\n")
    async def fake_exec(*a, **k): return _FakeProc(0, b"[]", b"")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="x=1", entry_point="N",
                        interface_spec={}, test_oracle={}, workspace=tmp_path)
    res = await PylintRosCheck().run(ctx)
    assert res.passed and res.execution.status == "OK"

@pytest.mark.asyncio
async def test_pylint_fail_findings(monkeypatch, tmp_path):
    (tmp_path / "candidate_node.py").write_text("x=1\n")
    findings = [{"type": "warning", "message-id": "W9001"}]
    async def fake_exec(*a, **k): return _FakeProc(4, json.dumps(findings).encode(), b"")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="x=1", entry_point="N",
                        interface_spec={}, test_oracle={}, workspace=tmp_path)
    res = await PylintRosCheck().run(ctx)
    assert not res.passed and res.execution.status == "FAIL"

@pytest.mark.asyncio
async def test_pylint_crash_fatal_bit(monkeypatch, tmp_path):
    (tmp_path / "candidate_node.py").write_text("x=1\n")
    async def fake_exec(*a, **k): return _FakeProc(32, b"", b"fatal")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_exec)
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="x=1", entry_point="N",
                        interface_spec={}, test_oracle={}, workspace=tmp_path)
    res = await PylintRosCheck().run(ctx)
    assert res.execution.status == "CRASH"
