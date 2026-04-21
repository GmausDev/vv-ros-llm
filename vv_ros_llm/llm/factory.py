from __future__ import annotations

from .base import LLMProvider


def build_provider(name: str, settings) -> LLMProvider:
    """Build a provider from a loaded Settings instance. `name` is 'openai'|'anthropic'|'ollama'."""
    name = name.lower()
    llm_cfg = settings.llm
    if name == "openai":
        from .openai_provider import OpenAIProvider

        cfg = llm_cfg.openai
        key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else ""
        )
        return OpenAIProvider(
            model=cfg.model,
            api_key=key,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            base_url=cfg.base_url,
        )
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider

        cfg = llm_cfg.anthropic
        key = (
            settings.anthropic_api_key.get_secret_value()
            if settings.anthropic_api_key
            else ""
        )
        return AnthropicProvider(
            model=cfg.model,
            api_key=key,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    if name == "ollama":
        from .ollama_provider import OllamaProvider

        cfg = llm_cfg.ollama
        return OllamaProvider(
            model=cfg.model,
            base_url=cfg.base_url or "http://localhost:11434",
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    raise ValueError(f"Unknown LLM provider: {name!r}")
