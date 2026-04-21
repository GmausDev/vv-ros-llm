"""Results aggregation, plots, and report rendering."""
from .aggregate import (
    summarize_by_model, summarize_by_difficulty, summarize_by_node_type,
    pass_at_k_by_model, latency_token_summary,
)
from .plots import save_pass_at_k_bar, save_model_difficulty_heatmap, save_latency_hist
from .report import build_report

__all__ = [
    "summarize_by_model", "summarize_by_difficulty", "summarize_by_node_type",
    "pass_at_k_by_model", "latency_token_summary",
    "save_pass_at_k_bar", "save_model_difficulty_heatmap", "save_latency_hist",
    "build_report",
]
