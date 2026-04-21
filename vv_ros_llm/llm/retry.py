from __future__ import annotations

import logging

from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

log = logging.getLogger(__name__)


class RetryableLLMError(Exception):
    """Network or rate-limit error worth retrying."""


def llm_retry(max_attempts: int = 3, max_wait: float = 30.0) -> AsyncRetrying:
    """Return a configured AsyncRetrying for LLM calls (429, 5xx, timeouts)."""
    return AsyncRetrying(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=1, max=max_wait),
        retry=retry_if_exception_type(RetryableLLMError),
        before_sleep=before_sleep_log(log, logging.WARNING),
    )
