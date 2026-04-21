from __future__ import annotations
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import pandas as pd

from vv_ros_llm.metrics.exporter import runs_dataframe, experiment_pass_at_k
from vv_ros_llm.metrics.store import MetricsStore
from .aggregate import (
    summarize_by_model, summarize_by_difficulty, summarize_by_node_type,
    pass_at_k_by_model,
)
from .plots import save_pass_at_k_bar, save_model_difficulty_heatmap, save_latency_hist

TEMPLATES = Path(__file__).parent / "templates"


def _df_md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False) if not df.empty else "_(no data)_"


def _png_b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def build_report(
    store: MetricsStore, experiment_id: str, output_dir: Path,
    tasks_meta: pd.DataFrame | None = None, fmt: str = "md",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    by_model = summarize_by_model(store, experiment_id)
    by_diff = summarize_by_difficulty(store, experiment_id, tasks_meta)
    by_node = summarize_by_node_type(store, experiment_id, tasks_meta)
    passk = pass_at_k_by_model(store, experiment_id, k_values=[1, 5, 10])
    overall_k = experiment_pass_at_k(store, experiment_id, [1, 5, 10])
    runs = runs_dataframe(store, experiment_id)

    heatmap_df = pd.DataFrame()
    if not runs.empty and tasks_meta is not None and "difficulty" in tasks_meta.columns:
        merged = runs.merge(tasks_meta[["task_id", "difficulty"]], on="task_id", how="left")
        heatmap_df = merged.groupby(["model", "difficulty"]).agg(
            pass_rate=("overall_pass", "mean")
        ).reset_index()

    p_bar = save_pass_at_k_bar(passk, output_dir / "pass_at_1.png", k=1)
    p_heat = save_model_difficulty_heatmap(heatmap_df, output_dir / "model_difficulty.png")
    p_lat = save_latency_hist(runs, output_dir / "latency_hist.png")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape())
    tmpl = env.get_template(f"report.{fmt}.j2")
    ctx = {
        "experiment_id": experiment_id,
        "overall_pass_at_k": overall_k,
        "by_model_md": _df_md(by_model),
        "by_diff_md": _df_md(by_diff),
        "by_node_md": _df_md(by_node),
        "passk_md": _df_md(passk),
        "plot_bar_png": p_bar.name if fmt == "md" else _png_b64(p_bar),
        "plot_heat_png": p_heat.name if fmt == "md" else _png_b64(p_heat),
        "plot_lat_png": p_lat.name if fmt == "md" else _png_b64(p_lat),
    }
    out = output_dir / ("report.md" if fmt == "md" else "report.html")
    out.write_text(tmpl.render(**ctx), encoding="utf-8")
    return out
