from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # headless — must come before pyplot
import matplotlib.pyplot as plt
import pandas as pd


def save_pass_at_k_bar(df: pd.DataFrame, out_path: Path, k: int = 1) -> Path:
    col = f"pass@{k}"
    if df.empty or col not in df.columns:
        return _placeholder(out_path, f"No data for {col}")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(df["model"].astype(str), df[col])
    ax.set_ylabel(col)
    ax.set_xlabel("model")
    ax.set_title(f"{col} by model")
    ax.set_ylim(0, 1)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def save_model_difficulty_heatmap(df: pd.DataFrame, out_path: Path) -> Path:
    if df.empty or not {"model", "difficulty", "pass_rate"}.issubset(df.columns):
        return _placeholder(out_path, "No model×difficulty data")
    piv = df.pivot_table(index="model", columns="difficulty", values="pass_rate", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(piv.values, aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels(piv.columns)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index)
    ax.set_title("pass_rate model × difficulty")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def save_latency_hist(df: pd.DataFrame, out_path: Path) -> Path:
    if df.empty or "latency_ms" not in df.columns:
        return _placeholder(out_path, "No latency data")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(df["latency_ms"].dropna(), bins=20)
    ax.set_xlabel("latency (ms)")
    ax.set_ylabel("count")
    ax.set_title("Generation latency")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def _placeholder(out_path: Path, msg: str) -> Path:
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.text(0.5, 0.5, msg, ha="center", va="center")
    ax.set_axis_off()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
