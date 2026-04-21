"""Settings loader backed by pydantic-settings with YAML + env support."""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import AliasChoices, BaseModel, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class LLMProviderConfig(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: str | None = None


class LLMConfig(BaseModel):
    openai: LLMProviderConfig
    anthropic: LLMProviderConfig
    ollama: LLMProviderConfig


class DockerConfig(BaseModel):
    image: str = "vv-ros-executor:humble"
    timeout: int = 120
    memory_limit: str = "4g"
    cpus: float = 2.0
    network: str = "none"


class VVPipelineConfig(BaseModel):
    enabled_methods: list[str] = ["ruff", "pylint_ros", "pytest", "hypothesis"]


class BenchmarksConfig(BaseModel):
    data_path: Path = Path("data/roseval_benchmarks.jsonl")
    filter_difficulty: str | None = None
    filter_node_type: str | None = None


class MetricsConfig(BaseModel):
    db_path: Path = Path("results/metrics.db")
    export_csv: bool = True


class ExperimentConfig(BaseModel):
    n_candidates: int = 5
    selection_strategy: str = "quality_metric"
    k_values: list[int] = [1, 5, 10]
    parallel_containers: int = 4


class _YamlSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], path: Path) -> None:
        super().__init__(settings_cls)
        self._data: dict[str, Any] = {}
        if path.is_file():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            llm_raw = raw.get("llm")
            if isinstance(llm_raw, dict) and "providers" in llm_raw:
                raw["llm"] = llm_raw["providers"]
            self._data = raw

    def get_field_value(self, field, field_name):  # type: ignore[override]
        value = self._data.get(field_name)
        return value, field_name, False

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._data.items() if v is not None}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VV_ROS_LLM_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm: LLMConfig
    docker: DockerConfig = DockerConfig()
    vv_pipeline: VVPipelineConfig = VVPipelineConfig()
    benchmarks: BenchmarksConfig = BenchmarksConfig()
    metrics: MetricsConfig = MetricsConfig()
    experiment: ExperimentConfig = ExperimentConfig()

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "VV_ROS_LLM_OPENAI_API_KEY"),
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "VV_ROS_LLM_ANTHROPIC_API_KEY"),
    )
    log_level: str = "INFO"

    _yaml_path_override: ClassVar[Path | None] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        yaml_path = cls._yaml_path_override or Path("config/default.yaml")
        yaml_source = _YamlSource(settings_cls, yaml_path)
        return (init_settings, env_settings, dotenv_settings, yaml_source, file_secret_settings)


def load_settings(config_path: Path | str = "config/default.yaml") -> Settings:
    """Load Settings with YAML at lower priority than env/.env."""
    path = Path(config_path)
    if path.name != "default.yaml" and not path.is_file():
        raise FileNotFoundError(f"config file not found: {path}")
    Settings._yaml_path_override = path
    try:
        return Settings()
    finally:
        Settings._yaml_path_override = None
