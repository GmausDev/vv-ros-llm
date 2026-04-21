from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from .store import MetricsStore
from .pass_at_k import pass_at_k_by_task

if TYPE_CHECKING:
    import pandas as pd


def runs_dataframe(store: MetricsStore, experiment_id: str) -> "pd.DataFrame":
    import pandas as pd
    rows = store.query_runs(experiment_id)
    data = [dict(r) for r in rows]
    df = pd.DataFrame(data)
    return df


def export_runs_csv(store: MetricsStore, experiment_id: str, out_path: Path | str) -> Path:
    import pandas as pd  # noqa: F401
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = runs_dataframe(store, experiment_id)
    df.to_csv(out, index=False)
    return out


def experiment_pass_at_k(
    store: MetricsStore, experiment_id: str, k_values: list[int] | None = None,
) -> dict[int, float]:
    import pandas as pd  # noqa: F401
    k_values = k_values or [1, 5, 10]
    df = runs_dataframe(store, experiment_id)
    if df.empty:
        return {k: 0.0 for k in k_values}
    counts: dict[str, tuple[int, int]] = {}
    for task_id, grp in df.groupby("task_id"):
        n = int(len(grp))
        c = int(grp["overall_pass"].sum())
        counts[str(task_id)] = (n, c)
    return pass_at_k_by_task(counts, k_values)
