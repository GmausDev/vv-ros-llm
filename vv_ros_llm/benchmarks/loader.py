from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from pydantic import ValidationError
from .schema import BenchmarkTask


@dataclass
class LoadError:
    line_no: int
    raw: str
    error: str


def load_jsonl(path: Path | str, strict: bool = False) -> tuple[list[BenchmarkTask], list[LoadError]]:
    """Load JSONL benchmarks. Returns (tasks, errors). Skips malformed lines when strict=False."""
    path = Path(path)
    tasks: list[BenchmarkTask] = []
    errors: list[LoadError] = []
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                tasks.append(BenchmarkTask.model_validate(data))
            except (json.JSONDecodeError, ValidationError) as e:
                err = LoadError(line_no=i, raw=line[:200], error=str(e))
                errors.append(err)
                if strict:
                    raise
    return tasks, errors


def filter_by(
    tasks: Iterable[BenchmarkTask],
    difficulty: str | None = None,
    node_type: str | None = None,
) -> list[BenchmarkTask]:
    out = list(tasks)
    if difficulty:
        diff = difficulty.lower()
        out = [t for t in out if t.difficulty.lower() == diff]
    if node_type:
        out = [t for t in out if t.node_type == node_type]
    return out
