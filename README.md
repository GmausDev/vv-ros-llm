# vv-ros-llm

Verification & Validation framework for LLM-generated ROS 2 code. Generates, tests, and evaluates robot software produced by multiple LLM providers inside sandboxed Docker containers.

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```bash
vv-ros-llm --help
```

## Project Structure

```
vv_ros_llm/        Core package
  llm/             LLM provider adapters (OpenAI, Anthropic, Ollama)
  vv/              Verification & validation pipeline
  benchmarks/      Benchmark loader and definitions
  metrics/         Metrics collection and storage
  experiment/      Experiment orchestration
  analysis/        Results analysis and visualization
tests/             Test suite
config/            YAML configuration files
data/              Benchmark datasets
docker/            Dockerfiles for ROS 2 execution sandbox
results/           Experiment output (git-ignored)
```

## Development

```bash
make install       # Install in editable mode with dev deps
make test          # Run test suite
make lint          # Run ruff + mypy
make format        # Auto-format with ruff
```
