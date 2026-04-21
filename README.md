# vv-ros-llm

**An evaluation harness that answers a simple question: when an LLM writes ROS 2 code, does it actually work?**

## The problem

Modern LLMs (GPT-4o, Claude, Llama-3, …) can draft ROS 2 nodes in Python on demand. But a plausible-looking `rclpy` snippet is not the same as a node that *runs*, publishes the right topics, respects QoS, or passes an oracle test. Human inspection doesn't scale across providers, models, prompts, and difficulty tiers, and it can't produce the kind of repeatable metrics needed for research or model-selection decisions.

## What vv-ros-llm does

`vv-ros-llm` is an end-to-end benchmark runner that, for each task:

1. **Loads a ROSEval-style benchmark** — a natural-language prompt plus a structured `interface_spec` (topics published/subscribed, services, parameters, QoS) and a `test_oracle` of machine-checkable assertions.
2. **Asks an LLM for N candidate completions** via a pluggable provider layer (OpenAI, Anthropic, or Ollama), with retries on rate limits / 5xx and reproducible per-candidate seeds.
3. **Drops each candidate into a locked-down ROS 2 Humble Docker sandbox** (network disabled, memory/CPU capped, 120 s timeout, non-root user).
4. **Runs a multi-method V&V pipeline** on every candidate:
   - `ruff` — syntax/style gate.
   - `pylint_ros` — a custom pylint plugin with ROS-specific checkers (missing `rclpy.init/shutdown/destroy_node`, blocking calls in callbacks, missing QoS depth).
   - `pytest` — oracle-derived tests executed inside the sandbox.
   - `hypothesis` — property-based checks on the interface spec.
   - `z3` — invariants such as topic-name uniqueness and QoS depth ≥ 1.
5. **Persists everything to SQLite** with WAL mode and a unique `(experiment, task, candidate)` key so interrupted runs can resume without re-calling paid APIs.
6. **Computes pass@k** using the HumanEval unbiased estimator and exports CSV / Markdown / HTML reports with Matplotlib plots (pass@k by difficulty, model × difficulty heatmaps, latency histograms).

The output is a reproducible, provider-agnostic score of how well any LLM writes runnable ROS 2 code, with per-task breakdowns you can slice by difficulty, node type, ROS concept, or model.

## Who it's for

- **Researchers** comparing LLM providers on robotics code synthesis.
- **Teams evaluating model upgrades** (does Claude 4.6 regress on publisher nodes vs 4.5?).
- **Benchmark authors** extending ROSEval with new tasks and oracle checks.
- **Robotics engineers** who want a CI-style gate before trusting LLM output in a real ROS workspace.

## Requirements

- Python 3.12+
- Docker (for the ROS 2 Humble sandbox image)
- API key for OpenAI and/or Anthropic, or a local Ollama server

## Install

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# 1. credentials
cp .env.example .env
# edit .env: OPENAI_API_KEY=..., ANTHROPIC_API_KEY=...

# 2. build the ROS 2 Humble sandbox (one-time, ~600 MB)
make docker-build
vv-ros-llm docker check

# 3. initialize the metrics DB
vv-ros-llm db init

# 4. explore benchmarks
vv-ros-llm benchmarks list
vv-ros-llm benchmarks show ROSEval/0

# 5. run an experiment (5 candidates per task, OpenAI provider)
vv-ros-llm experiment run --provider openai --n 5

# 6. inspect results
vv-ros-llm experiment status <experiment-id>
vv-ros-llm analyze pass-at-k <experiment-id>
vv-ros-llm analyze export-csv <experiment-id> -o results/runs.csv
```

## CLI reference

```
vv-ros-llm
  --config PATH          # override config file (default: config/default.yaml)
  --log-level LEVEL      # DEBUG | INFO | WARNING | ERROR
  --version

  benchmarks list        [--difficulty EASY|MEDIUM|HARD] [--node-type TYPE]
  benchmarks show        TASK_ID

  experiment run         --provider openai|anthropic|ollama
                         [--n N] [--task-ids A,B,C]
                         [--difficulty ...] [--node-type ...]
                         [--resume] [--experiment-id ID]
  experiment status      EXPERIMENT_ID

  analyze pass-at-k      EXPERIMENT_ID [--k 1,5,10]
  analyze export-csv     EXPERIMENT_ID [--output PATH]

  db init
  db path

  docker build
  docker check
```

## How it fits together

```
 ┌─────────────────┐     ┌───────────────┐     ┌──────────────────┐
 │ ROSEval         │     │ LLM Provider  │     │ ROS 2 Sandbox    │
 │ benchmark (JSON)│ ──▶ │ (OpenAI/      │ ──▶ │ (Docker, humble, │
 │  prompt +       │     │  Anthropic/   │     │  network=none,   │
 │  interface_spec │     │  Ollama)      │     │  4 GB, 120 s)    │
 │  + test_oracle  │     │  × N cand.    │     │                  │
 └─────────────────┘     └───────────────┘     └────────┬─────────┘
                                                         │
                     ┌──────────────────┐    ┌───────────▼───────────┐
                     │ SQLite metrics   │◀── │ V&V pipeline          │
                     │ (WAL, resumable) │    │  ruff, pylint_ros,    │
                     │                  │    │  pytest, hypothesis,  │
                     │                  │    │  z3                   │
                     └─────────┬────────┘    └───────────────────────┘
                               │
                  ┌────────────▼──────────────┐
                  │ analyze: pass@k, CSV,     │
                  │ Markdown/HTML + plots     │
                  └───────────────────────────┘
```

## Configuration

Precedence (highest first): CLI flags → environment variables (`VV_ROS_LLM_*`) → `.env` → `config/default.yaml` → defaults. Nested keys use `__` as the env delimiter, e.g. `VV_ROS_LLM_DOCKER__TIMEOUT=180`. API keys are read from `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, stored as `SecretStr`, and never logged.

Key config sections in `config/default.yaml`:

- `llm.providers.{openai,anthropic,ollama}` — model, temperature, max_tokens, base_url.
- `docker` — image, timeout, memory_limit, cpus, network (default `none`).
- `vv_pipeline.enabled_methods` — which V&V methods run, in order.
- `benchmarks.data_path` / filters.
- `experiment.n_candidates` / `k_values` / `parallel_containers`.

## Providers

| Provider | SDK | Auth | Notes |
|----------|-----|------|-------|
| OpenAI | `openai>=1.40` | `OPENAI_API_KEY` | Uses `seed` for reproducibility; `tiktoken` for token counts. |
| Anthropic | `anthropic>=0.86` | `ANTHROPIC_API_KEY` | No `seed` parameter — diversity driven by temperature. |
| Ollama | `httpx` | none | Defaults to `http://localhost:11434`. |

All providers retry on 429 / 5xx / timeouts via `tenacity` with exponential jitter.

## V&V methods

| Method | Where | Gates `overall_pass` | Purpose |
|--------|-------|----------------------|---------|
| `ruff` | host | yes | Syntax / style |
| `pylint_ros` | host | no (informational) | Custom ROS-aware checks |
| `pytest` | sandbox | yes | Oracle-derived runtime tests |
| `hypothesis` | host | no | Property / structural checks on interface spec |
| `z3` | host | no | Interface-spec invariants |

`overall_pass` is intentionally conservative: it gates on `{ruff, pytest}` by default so a candidate has to both parse-clean and pass the oracle, while the other methods contribute findings for post-hoc analysis.

## Project structure

```
vv_ros_llm/
  cli.py                  # Typer entry point (vv-ros-llm)
  commands/               # benchmarks / experiment / analyze / db / docker sub-apps
  config.py               # Pydantic-settings (YAML + env precedence)
  schemas.py              # Pydantic v2 result models
  logging.py              # Rich + rotating file handler

  llm/                    # Provider adapters + Jinja2 prompt templates
    base.py, prompt_template.py, retry.py, factory.py
    openai_provider.py, anthropic_provider.py, ollama_provider.py
    templates/{system,task,fewshot}.j2

  benchmarks/             # ROSEval JSONL loader + permissive schema
  vv/                     # Sandbox + methods + pipeline
    sandbox.py, assembler.py, pipeline.py, oracle_runner.py
    ruff_check.py, pylint_ros.py, pylint_ros_plugin.py
    pytest_runner.py, hypothesis_runner.py, z3_checks.py
  metrics/                # SQLite (WAL) + pass@k + CSV exporter
  experiment/             # Async runner, selection, resume
  analysis/               # pandas aggregation + matplotlib plots + report

tests/                    # unit / integration / property / smoke
config/                   # YAML configuration
data/                     # ROSEval benchmarks (roseval_benchmarks.jsonl)
docker/                   # ROS 2 Humble Dockerfile + entrypoint
results/                  # Experiment output (git-ignored)
```

## Development

```bash
make install         # editable install with dev deps
make test            # full suite + 75 % coverage gate
make test-fast       # skip docker/slow/network markers (fast dev loop)
make test-smoke      # end-to-end smoke test (CLI, stubbed externals, <5 s)
make lint            # ruff + mypy
make format          # auto-fix
```

Test layout:

- `tests/unit/` — mocked, fast (< 1 s each).
- `tests/integration/` — cross-module with in-memory SQLite + stubs.
- `tests/property/` — Hypothesis invariants (pass@k, prompt render, benchmark roundtrip).
- `tests/smoke/` — full CLI pipeline with all externals stubbed.

## Status

MVP. 107 tests passing, 75 % coverage, 0 ruff findings. See `results/` and the `analyze` subcommand for real experiment output.

## License

TBD.
