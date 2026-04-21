from __future__ import annotations
from pathlib import Path
import pytest
from vv_ros_llm.benchmarks.loader import load_jsonl

REAL = Path("data/roseval_benchmarks.jsonl")

@pytest.mark.skipif(not REAL.exists(), reason="no real dataset present")
def test_all_real_records_roundtrip():
    tasks, errors = load_jsonl(REAL)
    assert not errors, f"unexpected load errors: {errors[:3]}"
    for t in tasks:
        data = t.model_dump()
        # Must at least preserve task_id after roundtrip
        assert data["task_id"] == t.task_id
