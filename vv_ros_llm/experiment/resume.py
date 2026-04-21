from __future__ import annotations
from vv_ros_llm.metrics.store import MetricsStore


class ResumeTracker:
    """Thin wrapper around store.existing_run_keys for idempotent resume semantics."""

    def __init__(self, store: MetricsStore, experiment_id: str) -> None:
        self.store = store
        self.experiment_id = experiment_id
        self._done: set[tuple[str, int]] = store.existing_run_keys(experiment_id)

    def is_done(self, task_id: str, candidate_idx: int) -> bool:
        return (task_id, candidate_idx) in self._done

    def mark_done(self, task_id: str, candidate_idx: int) -> None:
        self._done.add((task_id, candidate_idx))
