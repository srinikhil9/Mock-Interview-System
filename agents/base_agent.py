from __future__ import annotations

from typing import Dict, Any, Optional
import asyncio

from models import AgentMessage, MessageType, InterviewSession
from tools.llm_client import LLMClient, ChatMessage
from utils.logging import get_logger


class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.logger = get_logger(f"agent.{name}")
        self.state: Dict[str, Any] = {}
        self.llm = LLMClient()

    async def acomplete(self, system_prompt: str, user_content: str, temperature: float = 0.2) -> str:
        messages = [ChatMessage(role="user", content=user_content)]
        return await self.llm.acomplete(system_prompt, messages, temperature=temperature)

    async def handle(self, message: AgentMessage, session: InterviewSession) -> Optional[AgentMessage]:
        raise NotImplementedError

    def describe(self) -> str:
        return f"{self.name}: {self.role}"

