from __future__ import annotations
from datetime import datetime, timezone
import pytest
from pydantic import TypeAdapter, ValidationError

from vv_ros_llm.schemas import (
    GenerationResult, ExecutionResult, MethodResult, VerificationResult,
    RunRecord, ExperimentRecord, ExecutionStatus, OracleCheck,
)

def test_execution_status_enum_values():
    assert ExecutionStatus.OK == "OK"
    assert ExecutionStatus.TIMEOUT == "TIMEOUT"

def test_generation_result_roundtrip():
    g = GenerationResult(provider="openai", model="gpt-4o", task_id="t1",
                          candidate_idx=0, text="code")
    data = g.model_dump()
    assert GenerationResult.model_validate(data) == g

def test_method_result_defaults_and_extra_forbid():
    e = ExecutionResult(status=ExecutionStatus.OK)
    m = MethodResult(method="ruff", passed=True, execution=e)
    assert m.findings == []
    with pytest.raises(ValidationError):
        MethodResult(method="ruff", passed=True, execution=e, unknown="x")

def test_oracle_discriminator_resolves_node_exists():
    data = {"check_type": "node_exists", "node_name": "n1"}
    out = TypeAdapter(OracleCheck).validate_python(data)
    assert out.check_type == "node_exists"
    assert out.node_name == "n1"

def test_verification_result_aggregates():
    e_ok = ExecutionResult(status=ExecutionStatus.OK)
    vr = VerificationResult(task_id="t", candidate_idx=0, methods=[
        MethodResult(method="ruff", passed=True, execution=e_ok),
        MethodResult(method="pytest", passed=False, execution=e_ok),
    ], overall_pass=False)
    assert not vr.overall_pass

def test_run_record_created_at_defaults():
    g = GenerationResult(provider="x", model="x", task_id="x", candidate_idx=0, text="")
    r = RunRecord(run_id="r1", experiment_id="e1", task_id="t1", candidate_idx=0, generation=g)
    assert r.created_at.tzinfo == timezone.utc

def test_experiment_record_requires_started_at():
    rec = ExperimentRecord(experiment_id="e1", config_hash="h", config_json="{}",
                            started_at=datetime(2026,1,1,tzinfo=timezone.utc))
    assert rec.finished_at is None
