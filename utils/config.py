from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class AppConfig:
    openai_api_key: Optional[str]
    anthropic_api_key: Optional[str]
    model_preference: str
    request_timeout_seconds: int
    max_retries: int
    log_level: str


def load_config() -> AppConfig:
    return AppConfig(
        openai_api_key=(
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAI_KEY")
            or os.getenv("OPEN_API_KEY")
        ),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        model_preference=os.getenv("MODEL_PREFERENCE", "openai:gpt-4o-mini"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


