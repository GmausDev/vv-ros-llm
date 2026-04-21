.PHONY: install test test-fast test-smoke lint format docker-build run

install:
	pip install -e ".[dev]"

test:
	pytest --cov=vv_ros_llm

lint:
	ruff check vv_ros_llm tests
	mypy vv_ros_llm

format:
	ruff format vv_ros_llm tests
	ruff check --fix vv_ros_llm tests

docker-build:
	docker build -t vv-ros-executor:humble -f docker/Dockerfile .

run:
	vv-ros-llm --help

test-fast:
	pytest -q -m "not docker and not slow and not network"

test-smoke:
	pytest tests/smoke -q
