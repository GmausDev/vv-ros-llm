"""HumanEval pass@k estimator.

pass@k = 1 - C(n - c, k) / C(n, k)
  where n = total candidates, c = #passing candidates, k <= n.
Edge cases:
  - c == 0  -> 0.0
  - c == n  -> 1.0
  - n < k   -> 1.0 if c >= 1 else 0.0  (scope inflation; treat as ceiling)
"""
from __future__ import annotations
from math import comb


def pass_at_k(n: int, c: int, k: int) -> float:
    if n <= 0:
        return 0.0
    if c <= 0:
        return 0.0
    if c >= n:
        return 1.0
    if k >= n:
        return 1.0
    return 1.0 - (comb(n - c, k) / comb(n, k))


def pass_at_k_by_task(
    task_pass_counts: dict[str, tuple[int, int]],
    k_values: list[int],
) -> dict[int, float]:
    """Aggregate pass@k across tasks.

    Args:
        task_pass_counts: {task_id: (n_candidates, n_passing)}
        k_values: e.g. [1, 5, 10]

    Returns:
        {k: mean_pass_at_k_across_tasks}
    """
    out: dict[int, float] = {}
    for k in k_values:
        if not task_pass_counts:
            out[k] = 0.0
            continue
        values = [pass_at_k(n, c, k) for (n, c) in task_pass_counts.values()]
        out[k] = sum(values) / len(values)
    return out
