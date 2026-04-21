from __future__ import annotations
from vv_ros_llm.metrics.store import MetricsStore

def test_roundtrip_in_memory(tmp_path):
    store = MetricsStore(":memory:")
    store.insert_experiment("e1", "hh", "{}")
    store.insert_run(run_id="r1", experiment_id="e1", task_id="T1", candidate_idx=0,
                     provider="openai", model="gpt-4o", prompt_tokens=10, completion_tokens=20,
                     latency_ms=100.0, code="x=1", overall_pass=True)
    store.insert_method_result(run_id="r1", method="ruff", passed=True, status="OK", exit_code=0,
                                duration_ms=1.0, findings=[])
    rows = store.query_runs("e1")
    assert len(rows) == 1 and rows[0]["overall_pass"] == 1
    keys = store.existing_run_keys("e1")
    assert ("T1", 0) in keys
    store.close()
