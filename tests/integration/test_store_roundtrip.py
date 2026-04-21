from __future__ import annotations
from vv_ros_llm.metrics.store import MetricsStore

def test_full_roundtrip_and_resume():
    s = MetricsStore(":memory:")
    s.insert_experiment("E1", "h", "{}")
    for i in range(3):
        s.insert_run(run_id=f"E1:{i}", experiment_id="E1", task_id="T1", candidate_idx=i,
                     provider="p", model="m", overall_pass=(i % 2 == 0))
        s.insert_method_result(run_id=f"E1:{i}", method="ruff", passed=True, status="OK",
                                exit_code=0, duration_ms=1.0)
    rows = s.query_runs("E1")
    assert len(rows) == 3
    assert sum(r["overall_pass"] for r in rows) == 2
    keys = s.existing_run_keys("E1")
    assert keys == {("T1", 0), ("T1", 1), ("T1", 2)}
    s.finalize_experiment("E1")
    s.close()
