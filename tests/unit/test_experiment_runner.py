from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from vv_ros_llm.experiment.runner import ExperimentRunner
from vv_ros_llm.llm.base import GenerationOutput
from vv_ros_llm.schemas import (
    VerificationResult,
    MethodResult,
    ExecutionResult,
    ExecutionStatus,
)
from vv_ros_llm.benchmarks.schema import BenchmarkTask


def _task(task_id: str = "T1"):
    return BenchmarkTask.model_validate({
        "task_id": task_id,
        "node_type": "publisher",
        "difficulty": "Easy",
        "ros_concepts": ["publisher"],
        "prompt": "def x(): pass",
        "canonical_solution": "",
        "entry_point": "MyNode",
        "interface_spec": {
            "node_name": "n",
            "topics_published": [{"name": "/a", "type": "std_msgs/Int32"}],
        },
        "test_oracle": {"checks": []},
        "dependencies": ["rclpy"],
    })


def _settings(parallel: int = 2):
    return SimpleNamespace(experiment=SimpleNamespace(parallel_containers=parallel))


def _gen_output(code: str = "```python\nx=1\n```", error: str | None = None):
    return GenerationOutput(
        text=code,
        raw_response=code,
        prompt_tokens=1,
        completion_tokens=2,
        latency_ms=1.0,
        model="m",
        provider="p",
        seed=0,
        error=error,
    )


def _verif_ok():
    ex = ExecutionResult(status=ExecutionStatus.OK)
    return VerificationResult(
        task_id="T1",
        candidate_idx=0,
        overall_pass=True,
        methods=[
            MethodResult(method="ruff", passed=True, execution=ex),
            MethodResult(method="pytest", passed=True, execution=ex),
        ],
    )


@pytest.mark.asyncio
async def test_run_empty_benchmarks_returns_early(tmp_path):
    provider = SimpleNamespace(generate=AsyncMock(), provider_name="p", model="m")
    pipeline = SimpleNamespace(run=AsyncMock())
    store = MagicMock()
    store.existing_run_keys.return_value = set()
    r = ExperimentRunner(
        settings=_settings(),
        provider=provider,
        pipeline=pipeline,
        store=store,
        workspace_root=tmp_path,
    )
    await r.run(experiment_id="E1", benchmarks=[], n_candidates=3)
    provider.generate.assert_not_awaited()
    pipeline.run.assert_not_awaited()
    store.insert_run.assert_not_called()


@pytest.mark.asyncio
async def test_run_skips_done_keys_when_resume(tmp_path):
    provider = SimpleNamespace(
        generate=AsyncMock(return_value=[_gen_output()]),
        provider_name="p",
        model="m",
    )
    pipeline = SimpleNamespace(run=AsyncMock(return_value=_verif_ok()))
    store = MagicMock()
    store.existing_run_keys.return_value = {("T1", 0)}
    r = ExperimentRunner(
        settings=_settings(),
        provider=provider,
        pipeline=pipeline,
        store=store,
        workspace_root=tmp_path,
    )
    await r.run(
        experiment_id="E1", benchmarks=[_task("T1")], n_candidates=1, resume=True
    )
    provider.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_happy_path_writes_runs_and_methods(tmp_path):
    outputs = [_gen_output("```python\nx=1\n```")]
    provider = SimpleNamespace(
        generate=AsyncMock(return_value=outputs), provider_name="p", model="m"
    )
    pipeline = SimpleNamespace(run=AsyncMock(return_value=_verif_ok()))
    store = MagicMock()
    store.existing_run_keys.return_value = set()
    r = ExperimentRunner(
        settings=_settings(),
        provider=provider,
        pipeline=pipeline,
        store=store,
        workspace_root=tmp_path,
    )
    await r.run(experiment_id="E1", benchmarks=[_task("T1")], n_candidates=1)
    assert store.insert_run.call_count == 1
    assert store.insert_method_result.call_count == 2


@pytest.mark.asyncio
async def test_run_generation_failure_still_stores_run_with_error(tmp_path):
    provider = SimpleNamespace(
        generate=AsyncMock(side_effect=RuntimeError("boom")),
        provider_name="p",
        model="m",
    )
    pipeline = SimpleNamespace(run=AsyncMock())
    store = MagicMock()
    store.existing_run_keys.return_value = set()
    r = ExperimentRunner(
        settings=_settings(),
        provider=provider,
        pipeline=pipeline,
        store=store,
        workspace_root=tmp_path,
    )
    await r.run(experiment_id="E1", benchmarks=[_task("T1")], n_candidates=2)
    assert store.insert_run.call_count == 2
    pipeline.run.assert_not_awaited()
    for call in store.insert_run.call_args_list:
        assert call.kwargs["gen_error"] == "boom"
        assert call.kwargs["overall_pass"] is False


@pytest.mark.asyncio
async def test_run_pipeline_crash_still_stores_run(tmp_path):
    provider = SimpleNamespace(
        generate=AsyncMock(return_value=[_gen_output()]),
        provider_name="p",
        model="m",
    )
    pipeline = SimpleNamespace(run=AsyncMock(side_effect=RuntimeError("pipeline boom")))
    store = MagicMock()
    store.existing_run_keys.return_value = set()
    r = ExperimentRunner(
        settings=_settings(),
        provider=provider,
        pipeline=pipeline,
        store=store,
        workspace_root=tmp_path,
    )
    await r.run(experiment_id="E1", benchmarks=[_task("T1")], n_candidates=1)
    assert store.insert_run.call_count == 1
    assert store.insert_method_result.call_count == 0


@pytest.mark.asyncio
async def test_verify_skipped_when_no_code(tmp_path):
    outputs = [_gen_output(code="", error=None)]
    provider = SimpleNamespace(
        generate=AsyncMock(return_value=outputs), provider_name="p", model="m"
    )
    pipeline = SimpleNamespace(run=AsyncMock())
    store = MagicMock()
    store.existing_run_keys.return_value = set()
    r = ExperimentRunner(
        settings=_settings(),
        provider=provider,
        pipeline=pipeline,
        store=store,
        workspace_root=tmp_path,
    )
    await r.run(experiment_id="E1", benchmarks=[_task("T1")], n_candidates=1)
    pipeline.run.assert_not_awaited()
    store.insert_run.assert_called_once()
