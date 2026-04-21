"""Pydantic v2 models shared across the vv-ros-llm pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class ExecutionStatus(StrEnum):
    OK = "OK"
    FAIL = "FAIL"
    CRASH = "CRASH"
    TIMEOUT = "TIMEOUT"
    OOM = "OOM"
    SKIPPED = "SKIPPED"


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    task_id: str
    candidate_idx: int
    text: str
    raw_response: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    seed: int | None = None
    temperature: float | None = None
    error: str | None = None


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: float = 0.0
    timed_out: bool = False


class MethodResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["ruff", "pylint_ros", "pytest", "hypothesis", "z3"]
    passed: bool
    score: float | None = None
    findings: list[dict[str, Any]] = Field(default_factory=list)
    execution: ExecutionResult


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    candidate_idx: int
    methods: list[MethodResult] = Field(default_factory=list)
    overall_pass: bool = False


class NodeExistsCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: Literal["node_exists"] = "node_exists"
    node_name: str
    timeout_sec: float = 5.0


class TopicPublishedCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: Literal["topic_published"] = "topic_published"
    topic: str
    msg_type: str
    min_count: int = 1
    timeout_sec: float = 5.0


class TopicSubscribedCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: Literal["topic_subscribed"] = "topic_subscribed"
    topic: str
    msg_type: str
    timeout_sec: float = 5.0


class MessageContentCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: Literal["message_content"] = "message_content"
    topic: str
    field: str
    expected: Any


class LogOutputContainsCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: Literal["log_output_contains"] = "log_output_contains"
    pattern: str
    after_publish: bool = False
    timeout_sec: float = 5.0


class ServiceCalledCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: Literal["service_called"] = "service_called"
    service: str
    srv_type: str
    timeout_sec: float = 5.0


class ParameterValueCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: Literal["parameter_value"] = "parameter_value"
    node: str
    parameter: str
    expected: Any


OracleCheck = Annotated[
    Union[
        NodeExistsCheck,
        TopicPublishedCheck,
        TopicSubscribedCheck,
        MessageContentCheck,
        LogOutputContainsCheck,
        ServiceCalledCheck,
        ParameterValueCheck,
    ],
    Field(discriminator="check_type"),
]


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    experiment_id: str
    task_id: str
    candidate_idx: int
    generation: GenerationResult
    verification: VerificationResult | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    config_hash: str
    config_json: str
    started_at: datetime
    finished_at: datetime | None = None
    git_sha: str | None = None
