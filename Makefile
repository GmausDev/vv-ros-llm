.PHONY: install test lint format docker-build run

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
