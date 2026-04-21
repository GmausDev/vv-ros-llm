from __future__ import annotations
from hypothesis import given, settings, strategies as st
from vv_ros_llm.metrics.pass_at_k import pass_at_k

@settings(max_examples=200, deadline=None)
@given(n=st.integers(min_value=1, max_value=50),
       c=st.integers(min_value=0, max_value=50),
       k=st.integers(min_value=1, max_value=50))
def test_bounded_in_unit_interval(n, c, k):
    c = min(c, n)
    k = min(k, n)
    p = pass_at_k(n, c, k)
    assert 0.0 <= p <= 1.0

@settings(max_examples=150, deadline=None)
@given(n=st.integers(min_value=2, max_value=30),
       c1=st.integers(min_value=0, max_value=30),
       c2=st.integers(min_value=0, max_value=30),
       k=st.integers(min_value=1, max_value=30))
def test_monotonic_in_c(n, c1, c2, k):
    c1 = min(c1, n)
    c2 = min(c2, n)
    k = min(k, n)
    if c1 <= c2:
        assert pass_at_k(n, c1, k) <= pass_at_k(n, c2, k) + 1e-9
