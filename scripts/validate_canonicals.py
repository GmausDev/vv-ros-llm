#!/usr/bin/env python
"""Benchmark sanity check: run every canonical solution through the V&V pipeline.

The dataset follows the HumanEval convention — `prompt` is a code scaffold and
`canonical_solution` is the completion body. This script assembles the full
program (scaffold + body + a standard rclpy main() wrapper), then runs it
through the same VVPipeline used for LLM candidates. If every task passes its
own oracle, the benchmark is demonstrably solvable.

Usage (from the repo root, venv active or via .venv/bin/python):
    python scripts/validate_canonicals.py [--host-only] [--config PATH]

--host-only drops pytest (no Docker required) and checks the static methods
only; the full run needs the Docker sandbox image (`make docker-build`).

Exit code 0 iff every canonical passes all enabled methods.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

from vv_ros_llm.benchmarks.loader import load_jsonl
from vv_ros_llm.config import load_settings
from vv_ros_llm.vv.assembler import write_candidate_workspace
from vv_ros_llm.vv.base import MethodContext
from vv_ros_llm.vv.pipeline import VVPipeline
from vv_ros_llm.vv.sandbox import DockerSandbox, DockerSandboxConfig

MAIN_TEMPLATE = """

def main(args=None):
    rclpy.init(args=args)
    node = {entry_point}()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
"""


def assemble(task) -> str:
    """Scaffold + completion body + standard main() (HumanEval-style join)."""
    full = task.prompt + task.canonical_solution
    if "def main(" not in full:
        if "import rclpy" not in full:
            full = "import rclpy\n" + full
        full += MAIN_TEMPLATE.format(entry_point=task.entry_point)
    return full


async def validate(tasks, pipeline: VVPipeline) -> int:
    failures = 0
    for task in tasks:
        code = assemble(task)
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            write_candidate_workspace(
                ws,
                candidate_code=code,
                entry_point=task.entry_point,
                interface_spec=task.interface_spec.model_dump(),
                test_oracle=task.test_oracle.model_dump(),
            )
            ctx = MethodContext(
                task_id=task.task_id,
                candidate_idx=0,
                candidate_code=code,
                entry_point=task.entry_point,
                interface_spec=task.interface_spec.model_dump(),
                test_oracle=task.test_oracle.model_dump(),
                workspace=ws,
                dependencies=list(task.dependencies),
            )
            result = await pipeline.run(ctx)
        per_method = "  ".join(
            f"{m.method}={'OK' if m.passed else m.execution.status.value}"
            for m in result.methods
        )
        verdict = "PASS" if result.overall_pass else "FAIL"
        if not result.overall_pass:
            failures += 1
            for m in result.methods:
                if not m.passed and m.findings:
                    print(f"    {task.task_id} {m.method} findings: {m.findings[:3]}")
        print(f"{task.task_id:<12} {verdict}  [{per_method}]")
    return failures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host-only", action="store_true",
                    help="skip pytest/Docker; static + property methods only")
    ap.add_argument("--config", default="config/default.yaml")
    args = ap.parse_args()

    settings = load_settings(args.config)
    tasks, errors = load_jsonl(settings.benchmarks.data_path, strict=True)
    if errors:
        for e in errors:
            print(f"SCHEMA ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    methods = list(settings.vv_pipeline.enabled_methods)
    if args.host_only:
        methods = [m for m in methods if m != "pytest"]
        sandbox = None
    else:
        if "pytest" not in methods:
            methods.append("pytest")
        sandbox = DockerSandbox(DockerSandboxConfig(
            image=settings.docker.image,
            timeout=settings.docker.timeout,
            memory_limit=settings.docker.memory_limit,
            cpus=settings.docker.cpus,
            network=settings.docker.network,
        ))
        asyncio.run(sandbox.ensure_image())

    print(f"Validating {len(tasks)} canonical solutions "
          f"(methods: {', '.join(methods)})\n")
    pipeline = VVPipeline(methods, sandbox)
    failures = asyncio.run(validate(tasks, pipeline))

    print(f"\n{len(tasks) - failures}/{len(tasks)} canonical solutions pass")
    if sandbox is not None and hasattr(sandbox, "close"):
        sandbox.close()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
