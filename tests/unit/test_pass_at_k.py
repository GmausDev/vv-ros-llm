from __future__ import annotations
import pytest
from vv_ros_llm.metrics.pass_at_k import pass_at_k, pass_at_k_by_task

def test_c_zero():
    assert pass_at_k(5, 0, 1) == 0.0

def test_c_eq_n():
    assert pass_at_k(5, 5, 1) == 1.0

def test_uniform_unit_k():
    assert pass_at_k(5, 1, 1) == pytest.approx(0.2)

def test_half_sample_k5():
    assert pass_at_k(10, 1, 5) == pytest.approx(0.5)

def test_aggregate_per_task():
    out = pass_at_k_by_task({"A": (5, 1), "B": (5, 5)}, [1, 5])
    assert out[1] == pytest.approx(0.6)
    assert out[5] == pytest.approx(1.0)
