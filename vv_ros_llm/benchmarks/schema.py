from __future__ import annotations
from typing import Any, Literal, Union
from pydantic import BaseModel, ConfigDict


class TopicSpec(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    type: str


class InterfaceSpec(BaseModel):
    model_config = ConfigDict(extra="allow")
    node_name: str
    topics_published: list[TopicSpec] = []
    topics_subscribed: list[TopicSpec] = []
    services_provided: list[dict[str, Any]] = []
    services_used: list[dict[str, Any]] = []
    actions_provided: list[dict[str, Any]] = []
    actions_used: list[dict[str, Any]] = []
    parameters: list[dict[str, Any]] = []


class _OracleBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class NodeExistsCheck(_OracleBase):
    type: Literal["node_exists"] = "node_exists"
    node_name: str
    timeout_sec: float = 5.0


class TopicPublishedCheck(_OracleBase):
    type: Literal["topic_published"] = "topic_published"
    topic: str
    msg_type: str | None = None
    min_count: int = 1
    timeout_sec: float = 5.0


class TopicSubscribedCheck(_OracleBase):
    type: Literal["topic_subscribed"] = "topic_subscribed"
    topic: str
    msg_type: str | None = None
    timeout_sec: float = 5.0


class MessageContentCheck(_OracleBase):
    type: Literal["message_content"] = "message_content"
    topic: str
    field: str
    expected: Any


class LogOutputContainsCheck(_OracleBase):
    type: Literal["log_output_contains"] = "log_output_contains"
    pattern: str
    after_publish: Any = False
    timeout_sec: float = 5.0


class ServiceCalledCheck(_OracleBase):
    type: Literal["service_called"] = "service_called"
    service: str
    srv_type: str | None = None
    timeout_sec: float = 5.0


class ParameterValueCheck(_OracleBase):
    type: Literal["parameter_value"] = "parameter_value"
    node: str
    parameter: str
    expected: Any


class ParameterDeclaredCheck(_OracleBase):
    type: Literal["parameter_declared"] = "parameter_declared"
    node_name: str
    param_name: str
    param_type: str | None = None


class UnknownOracleCheck(_OracleBase):
    """Permissive fallback for oracle check types not explicitly modeled.

    Why: real benchmark data may introduce new check kinds; we don't want load to fail.
    How to apply: any record whose 'type' isn't one of the known literals deserializes here.
    """
    type: str


OracleCheck = Union[
    NodeExistsCheck, TopicPublishedCheck, TopicSubscribedCheck,
    MessageContentCheck, LogOutputContainsCheck,
    ServiceCalledCheck, ParameterValueCheck,
    ParameterDeclaredCheck, UnknownOracleCheck,
]


class TestOracle(BaseModel):
    model_config = ConfigDict(extra="allow")
    checks: list[OracleCheck] = []


Difficulty = Literal["Easy", "Medium", "Hard", "easy", "medium", "hard"]
NodeType = str


class BenchmarkTask(BaseModel):
    model_config = ConfigDict(extra="allow")
    task_id: str
    node_type: NodeType
    difficulty: Difficulty
    ros_concepts: list[str] = []
    prompt: str
    canonical_solution: str = ""
    entry_point: str
    interface_spec: InterfaceSpec
    test_oracle: TestOracle
    dependencies: list[str] = []
