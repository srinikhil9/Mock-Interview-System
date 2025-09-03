from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import asyncio
import json

from utils.config import load_config
from utils.logging import get_logger
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=False)
except Exception:
    pass


logger = get_logger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self):
        self.config = load_config()
        self._provider, self._model = self._parse_model_preference(self.config.model_preference)
        self._ready: bool = True
        self._unavailable_reason: Optional[str] = None
        # Preflight dependency and credential checks to avoid noisy retries
        try:
            if self._provider == "openai":
                if not self.config.openai_api_key:
                    self._ready = False
                    self._unavailable_reason = "missing_openai_api_key"
                else:
                    try:
                        import openai  # noqa: F401
                    except Exception:
                        self._ready = False
                        self._unavailable_reason = "missing_openai_package"
            elif self._provider == "anthropic":
                if not self.config.anthropic_api_key:
                    self._ready = False
                    self._unavailable_reason = "missing_anthropic_api_key"
                else:
                    try:
                        from anthropic import AsyncAnthropic  # noqa: F401
                    except Exception:
                        self._ready = False
                        self._unavailable_reason = "missing_anthropic_package"
        except Exception as e:
            # Any unexpected preflight error => mark as unavailable
            self._ready = False
            self._unavailable_reason = f"preflight_error:{e}"
        # One-time preflight log (no secrets)
        status = "ready" if self._ready else f"unavailable:{self._unavailable_reason}"
        logger.info(f"LLM preflight provider={self._provider} model={self._model} status={status}")

    @staticmethod
    def _parse_model_preference(pref: str) -> tuple[str, str]:
        if ":" in pref:
            provider, model = pref.split(":", 1)
        else:
            provider, model = "openai", pref
        return provider, model

    async def acomplete(self, system_prompt: str, messages: List[ChatMessage], temperature: float = 0.2) -> str:
        if not self._ready:
            reason = self._unavailable_reason or "provider_unavailable"
            logger.info(f"LLM provider unavailable: {reason}. Using fallback.")
            raise LLMError(reason)
        max_retries = self.config.max_retries
        timeout = self.config.request_timeout_seconds
        for attempt in range(1, max_retries + 1):
            try:
                if self._provider == "openai":
                    return await self._openai_complete(system_prompt, messages, temperature, timeout)
                elif self._provider == "anthropic":
                    return await self._anthropic_complete(system_prompt, messages, temperature, timeout)
                else:
                    raise LLMError(f"Unsupported provider: {self._provider}")
            except Exception as e:
                logger.warning(f"LLM request failed (attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    raise
                await asyncio.sleep(0.5 * attempt)

    async def _openai_complete(self, system_prompt: str, messages: List[ChatMessage], temperature: float, timeout: int) -> str:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.config.openai_api_key)
            full_messages = ([{"role": "system", "content": system_prompt}] +
                             [{"role": m.role, "content": m.content} for m in messages])
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self._model,
                    messages=full_messages,
                    temperature=temperature,
                ),
                timeout=timeout,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(str(e))

    async def _anthropic_complete(self, system_prompt: str, messages: List[ChatMessage], temperature: float, timeout: int) -> str:
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
            user_content = []
            for m in messages:
                if m.role == "user":
                    user_content.append({"type": "text", "text": m.content})
                elif m.role == "assistant":
                    # Anthropic API expects a linear conversation; we fold assistant messages into the running content
                    user_content.append({"type": "text", "text": f"Assistant: {m.content}"})
            resp = await asyncio.wait_for(
                client.messages.create(
                    model=self._model,
                    system=system_prompt,
                    max_tokens=800,
                    temperature=temperature,
                    messages=[{"role": "user", "content": user_content}],
                ),
                timeout=timeout,
            )
            return resp.content[0].text if resp.content else ""
        except Exception as e:
            raise LLMError(str(e))


