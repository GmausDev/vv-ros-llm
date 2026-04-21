from __future__ import annotations
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .schema import init_db

class MetricsStore:
    """Thread-safe SQLite metrics store (WAL mode, single-writer lock)."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self.db_path if str(self.db_path) != ":memory:" else ":memory:",
            check_same_thread=False,
            isolation_level=None,  # autocommit off, use BEGIN/COMMIT manually
        )
        self._conn.row_factory = sqlite3.Row
        init_db(self._conn)

    @contextmanager
    def txn(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                yield self._conn
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    # --- inserts -----------------------------------------------------------

    def insert_experiment(self, experiment_id: str, config_hash: str, config_json: str,
                          started_at: datetime | None = None, git_sha: str | None = None) -> None:
        started = (started_at or datetime.now(timezone.utc)).isoformat()
        with self.txn() as c:
            c.execute(
                "INSERT OR IGNORE INTO experiments(experiment_id, config_hash, config_json, started_at, git_sha) "
                "VALUES (?, ?, ?, ?, ?)",
                (experiment_id, config_hash, config_json, started, git_sha),
            )

    def finalize_experiment(self, experiment_id: str, finished_at: datetime | None = None) -> None:
        fin = (finished_at or datetime.now(timezone.utc)).isoformat()
        with self.txn() as c:
            c.execute("UPDATE experiments SET finished_at=? WHERE experiment_id=?", (fin, experiment_id))

    def insert_run(self, *, run_id: str, experiment_id: str, task_id: str, candidate_idx: int,
                   provider: str, model: str, prompt_tokens: int = 0, completion_tokens: int = 0,
                   latency_ms: float = 0.0, seed: int | None = None, code: str | None = None,
                   gen_error: str | None = None, overall_pass: bool = False,
                   created_at: datetime | None = None) -> None:
        ts = (created_at or datetime.now(timezone.utc)).isoformat()
        with self.txn() as c:
            c.execute(
                "INSERT OR REPLACE INTO runs(run_id, experiment_id, task_id, candidate_idx, provider, model, "
                "prompt_tokens, completion_tokens, latency_ms, seed, code, gen_error, overall_pass, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, experiment_id, task_id, candidate_idx, provider, model,
                 prompt_tokens, completion_tokens, latency_ms, seed, code, gen_error,
                 1 if overall_pass else 0, ts),
            )

    def insert_method_result(self, *, run_id: str, method: str, passed: bool, score: float | None = None,
                             status: str | None = None, exit_code: int | None = None,
                             duration_ms: float = 0.0, stdout: str = "", stderr: str = "",
                             findings: list | None = None) -> None:
        with self.txn() as c:
            c.execute(
                "INSERT INTO method_results(run_id, method, passed, score, status, exit_code, duration_ms, "
                "stdout, stderr, findings_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, method, 1 if passed else 0, score, status, exit_code, duration_ms,
                 stdout, stderr, json.dumps(findings or [])),
            )

    # --- queries -----------------------------------------------------------

    def existing_run_keys(self, experiment_id: str) -> set[tuple[str, int]]:
        """Return (task_id, candidate_idx) for runs that finished (passed OR explicit gen_error).

        Excludes runs that crashed mid-pipeline (no gen_error, overall_pass=0, no method rows)
        so resume retries them instead of silently skipping.
        """
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT r.task_id, r.candidate_idx
                FROM runs r
                WHERE r.experiment_id=?
                  AND (r.overall_pass=1
                       OR r.gen_error IS NOT NULL
                       OR EXISTS (SELECT 1 FROM method_results m WHERE m.run_id=r.run_id))
                """,
                (experiment_id,),
            ).fetchall()
        return {(r["task_id"], r["candidate_idx"]) for r in rows}

    def query_runs(self, experiment_id: str):
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM runs WHERE experiment_id=? ORDER BY task_id, candidate_idx",
                (experiment_id,),
            ).fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
