from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationOutput:
    """Local result type — Wave 2 providers convert to vv_ros_llm.schemas.GenerationResult."""
    text: str
    raw_response: str | None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    model: str
    provider: str
    seed: int | None = None
    error: str | None = None


class LLMProvider(ABC):
    """Abstract LLM provider. Implementations live in vv_ros_llm.llm.{openai,anthropic,ollama}_provider."""

    provider_name: str = "base"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        n: int = 1,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        seed: int | None = None,
    ) -> list[GenerationOutput]:
        """Generate n candidate completions for a prompt."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Best-effort token count."""
