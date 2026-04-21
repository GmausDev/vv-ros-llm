from __future__ import annotations
import pandas as pd

from vv_ros_llm.metrics.exporter import runs_dataframe
from vv_ros_llm.metrics.pass_at_k import pass_at_k_by_task
from vv_ros_llm.metrics.store import MetricsStore


def _ensure_metadata(df: pd.DataFrame, tasks_meta: pd.DataFrame | None) -> pd.DataFrame:
    if tasks_meta is None or df.empty:
        return df
    return df.merge(tasks_meta, on="task_id", how="left")


def summarize_by_model(store: MetricsStore, experiment_id: str) -> pd.DataFrame:
    df = runs_dataframe(store, experiment_id)
    if df.empty:
        return df
    g = df.groupby("model", dropna=False).agg(
        n=("run_id", "count"),
        passed=("overall_pass", "sum"),
        mean_latency_ms=("latency_ms", "mean"),
        tokens_in=("prompt_tokens", "sum"),
        tokens_out=("completion_tokens", "sum"),
    ).reset_index()
    g["pass_rate"] = g["passed"] / g["n"].clip(lower=1)
    return g


def summarize_by_difficulty(
    store: MetricsStore, experiment_id: str,
    tasks_meta: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = _ensure_metadata(runs_dataframe(store, experiment_id), tasks_meta)
    if df.empty or "difficulty" not in df.columns:
        return df
    g = df.groupby("difficulty", dropna=False).agg(
        n=("run_id", "count"),
        passed=("overall_pass", "sum"),
    ).reset_index()
    g["pass_rate"] = g["passed"] / g["n"].clip(lower=1)
    return g


def summarize_by_node_type(
    store: MetricsStore, experiment_id: str,
    tasks_meta: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = _ensure_metadata(runs_dataframe(store, experiment_id), tasks_meta)
    if df.empty or "node_type" not in df.columns:
        return df
    g = df.groupby("node_type", dropna=False).agg(
        n=("run_id", "count"),
        passed=("overall_pass", "sum"),
    ).reset_index()
    g["pass_rate"] = g["passed"] / g["n"].clip(lower=1)
    return g


def pass_at_k_by_model(
    store: MetricsStore, experiment_id: str,
    k_values: list[int] | None = None,
) -> pd.DataFrame:
    df = runs_dataframe(store, experiment_id)
    if df.empty:
        return df
    k_values = k_values or [1, 5, 10]
    rows: list[dict] = []
    for model, g in df.groupby("model", dropna=False):
        counts: dict[str, tuple[int, int]] = {}
        for task_id, gg in g.groupby("task_id"):
            n = int(len(gg))
            c = int(gg["overall_pass"].sum())
            counts[str(task_id)] = (n, c)
        res = pass_at_k_by_task(counts, k_values)
        row: dict = {"model": model}
        for k, v in res.items():
            row[f"pass@{k}"] = v
        rows.append(row)
    return pd.DataFrame(rows)


def latency_token_summary(store: MetricsStore, experiment_id: str) -> pd.DataFrame:
    df = runs_dataframe(store, experiment_id)
    if df.empty:
        return df
    return df.agg(
        mean_latency_ms=("latency_ms", "mean"),
        p95_latency_ms=("latency_ms", lambda s: s.quantile(0.95)),
        tokens_in=("prompt_tokens", "sum"),
        tokens_out=("completion_tokens", "sum"),
    ).to_frame().T
