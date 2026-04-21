-- vv-ros-llm metrics schema (SQLite, WAL mode)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    config_hash   TEXT NOT NULL,
    config_json   TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    git_sha       TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,
    experiment_id     TEXT NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    task_id           TEXT NOT NULL,
    candidate_idx     INTEGER NOT NULL,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    latency_ms        REAL DEFAULT 0.0,
    seed              INTEGER,
    code              TEXT,
    gen_error         TEXT,
    overall_pass      INTEGER DEFAULT 0,
    created_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_exp_task ON runs(experiment_id, task_id);
CREATE INDEX IF NOT EXISTS idx_runs_task_cand ON runs(task_id, candidate_idx);

CREATE TABLE IF NOT EXISTS method_results (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    method       TEXT NOT NULL,
    passed       INTEGER NOT NULL DEFAULT 0,
    score        REAL,
    status       TEXT,
    exit_code    INTEGER,
    duration_ms  REAL DEFAULT 0.0,
    stdout       TEXT,
    stderr       TEXT,
    findings_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_method_run ON method_results(run_id);
CREATE INDEX IF NOT EXISTS idx_method_name ON method_results(method);

-- Unique idempotency key for resume semantics.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_run_key ON runs(experiment_id, task_id, candidate_idx);
