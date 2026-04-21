from __future__ import annotations
import json
from pathlib import Path
import pytest

from vv_ros_llm.benchmarks.loader import load_jsonl, filter_by

def _valid_record(**overrides):
    base = {
        "task_id": "T1", "node_type": "publisher", "difficulty": "Easy",
        "ros_concepts": ["publisher"], "prompt": "stub", "canonical_solution": "",
        "entry_point": "MyNode",
        "interface_spec": {"node_name": "my_node", "topics_published": [{"name":"/x","type":"std_msgs/String"}]},
        "test_oracle": {"checks": []},
        "dependencies": ["rclpy"],
    }
    base.update(overrides)
    return base

def test_loads_valid_records(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    p.write_text("\n".join(json.dumps(_valid_record(task_id=f"T{i}")) for i in range(3)) + "\n")
    tasks, errs = load_jsonl(p)
    assert len(tasks) == 3 and not errs

def test_skips_malformed_nonstrict(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    p.write_text(json.dumps(_valid_record()) + "\nnot json\n")
    tasks, errs = load_jsonl(p, strict=False)
    assert len(tasks) == 1 and len(errs) == 1

def test_strict_raises(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    p.write_text("not json\n")
    with pytest.raises(Exception):
        load_jsonl(p, strict=True)

def test_filter_by_difficulty_and_node_type(tmp_path: Path):
    p = tmp_path / "b.jsonl"
    recs = [_valid_record(task_id="A", difficulty="Easy", node_type="publisher"),
            _valid_record(task_id="B", difficulty="Hard", node_type="subscriber")]
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    tasks, _ = load_jsonl(p)
    assert len(filter_by(tasks, difficulty="easy")) == 1
    assert len(filter_by(tasks, node_type="subscriber")) == 1

def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_jsonl(tmp_path / "missing.jsonl")
