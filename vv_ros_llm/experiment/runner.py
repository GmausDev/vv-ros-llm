from __future__ import annotations
import asyncio
import hashlib
import logging
import tempfile
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path

from vv_ros_llm.benchmarks.schema import BenchmarkTask
from vv_ros_llm.llm.base import LLMProvider, GenerationOutput
from vv_ros_llm.llm.prompt_template import PromptBuilder, extract_python_code
from vv_ros_llm.vv.assembler import write_candidate_workspace
from vv_ros_llm.vv.base import MethodContext
from vv_ros_llm.vv.pipeline import VVPipeline
from vv_ros_llm.metrics.store import MetricsStore

log = logging.getLogger(__name__)


def _run_id(experiment_id: str, task_id: str, candidate_idx: int) -> str:
    h = hashlib.sha1(
        f"{experiment_id}\x00{task_id}\x00{candidate_idx}".encode()
    ).hexdigest()[:16]
    return f"{experiment_id}-{h}"


@dataclass
class _CandidateWork:
    task: BenchmarkTask
    candidate_idx: int
    seed: int | None


class ExperimentRunner:
    def __init__(self, *, settings, provider: LLMProvider, pipeline: VVPipeline,
                 store: MetricsStore, prompt_builder: PromptBuilder | None = None,
                 workspace_root: Path | None = None) -> None:
        self.settings = settings
        self.provider = provider
        self.pipeline = pipeline
        self.store = store
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.workspace_root = workspace_root
        self._sema = asyncio.Semaphore(settings.experiment.parallel_containers)

    async def run(self, *, experiment_id: str, benchmarks: list[BenchmarkTask],
                  n_candidates: int, resume: bool = False, base_seed: int | None = 0) -> None:
        done_keys = self.store.existing_run_keys(experiment_id) if resume else set()
        work: list[_CandidateWork] = []
        for task in benchmarks:
            for i in range(n_candidates):
                if (task.task_id, i) in done_keys:
                    continue
                seed = None if base_seed is None else base_seed + i
                work.append(_CandidateWork(task=task, candidate_idx=i, seed=seed))
        log.info("ExperimentRunner: %d candidates across %d tasks (%d skipped via resume)",
                 len(work), len(benchmarks), len(benchmarks) * n_candidates - len(work))
        if not work:
            return

        tasks_by_id: dict[str, list[_CandidateWork]] = {}
        for w in work:
            tasks_by_id.setdefault(w.task.task_id, []).append(w)

        async with AsyncExitStack():
            coros = [self._process_task(experiment_id, tasks_by_id[tid], tasks_by_id[tid][0].task)
                     for tid in tasks_by_id]
            results = await asyncio.gather(*coros, return_exceptions=True)
            for r in results:
                if isinstance(r, BaseException):
                    log.exception("task-level error: %s", r)

    async def _process_task(self, experiment_id: str, items: list[_CandidateWork],
                            task: BenchmarkTask) -> None:
        prompt = self.prompt_builder.render(task.model_dump(), ros_distro="humble")
        n = len(items)
        base = items[0].seed
        try:
            outputs: list[GenerationOutput] = await self.provider.generate(
                prompt=prompt, n=n, seed=base
            )
        except Exception as e:
            log.exception("Generation failed for %s: %s", task.task_id, e)
            outputs = [GenerationOutput(
                text="", raw_response=None, prompt_tokens=0,
                completion_tokens=0, latency_ms=0.0,
                model=getattr(self.provider, "model", ""),
                provider=self.provider.provider_name, seed=None,
                error=str(e),
            ) for _ in items]

        cand_results = await asyncio.gather(
            *[self._verify_candidate(experiment_id, item, out)
              for item, out in zip(items, outputs)],
            return_exceptions=True,
        )
        for r in cand_results:
            if isinstance(r, BaseException):
                log.exception("candidate-level error on %s: %s", task.task_id, r)

    async def _verify_candidate(self, experiment_id: str, item: _CandidateWork,
                                output: GenerationOutput) -> None:
        run_id = _run_id(experiment_id, item.task.task_id, item.candidate_idx)
        code = extract_python_code(output.text) if output.text else ""
        verification = None
        overall_pass = False
        if not output.error and code:
            async with self._sema:
                with tempfile.TemporaryDirectory(dir=self.workspace_root) as td:
                    ws = Path(td)
                    write_candidate_workspace(
                        ws, candidate_code=code, entry_point=item.task.entry_point,
                        interface_spec=item.task.interface_spec.model_dump(),
                        test_oracle=item.task.test_oracle.model_dump(),
                    )
                    ctx = MethodContext(
                        task_id=item.task.task_id, candidate_idx=item.candidate_idx,
                        candidate_code=code, entry_point=item.task.entry_point,
                        interface_spec=item.task.interface_spec.model_dump(),
                        test_oracle=item.task.test_oracle.model_dump(),
                        workspace=ws, dependencies=list(item.task.dependencies),
                    )
                    try:
                        verification = await self.pipeline.run(ctx)
                        overall_pass = verification.overall_pass
                    except Exception as e:
                        log.exception("Pipeline crashed on %s/%d: %s",
                                      item.task.task_id, item.candidate_idx, e)

        self.store.insert_run(
            run_id=run_id, experiment_id=experiment_id,
            task_id=item.task.task_id, candidate_idx=item.candidate_idx,
            provider=output.provider, model=output.model,
            prompt_tokens=output.prompt_tokens, completion_tokens=output.completion_tokens,
            latency_ms=output.latency_ms, seed=output.seed, code=code or None,
            gen_error=output.error, overall_pass=overall_pass,
        )
        if verification is not None:
            for mr in verification.methods:
                self.store.insert_method_result(
                    run_id=run_id, method=mr.method, passed=mr.passed, score=mr.score,
                    status=mr.execution.status.value,
                    exit_code=mr.execution.exit_code, duration_ms=mr.execution.duration_ms,
                    stdout=mr.execution.stdout[:4000] if mr.execution.stdout else "",
                    stderr=mr.execution.stderr[:4000] if mr.execution.stderr else "",
                    findings=list(mr.findings or []),
                )
