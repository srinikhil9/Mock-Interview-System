from __future__ import annotations

from typing import Optional

from models import AgentMessage, MessageType, InterviewSession
from .base_agent import BaseAgent


HINTS_SYSTEM = (
    "You are a helpful interview coach. Based on the feedback and topic, give ONE short hint (<=20 words) "
    "that nudges the candidate toward a stronger answer. Do NOT reveal the full answer."
)


class HintsAgent(BaseAgent):
    async def handle(self, message: AgentMessage, session: InterviewSession) -> Optional[AgentMessage]:
        if message.type != MessageType.EVALUATION:
            return None
        topic = message.topic or (session.topic_plan.current().topic.name if session.topic_plan.current() else "General")
        feedback = message.content
        user = (
            f"Topic: {topic}\n"
            f"Feedback: {feedback}\n"
            f"Strengths: {message.metadata.get('strengths', [])}\n"
            f"Improvements: {message.metadata.get('improvements', [])}\n"
            "Return ONE hint only."
        )
        try:
            hint = await self.acomplete(HINTS_SYSTEM, user)
            hint = (hint or "").strip()
            if len(hint) > 140:
                hint = hint[:137] + "..."
        except Exception as e:
            self.logger.info(f"Using hints fallback: {e}")
            hint = "Be specific: cite an example, metrics, and tradeoffs."
        return AgentMessage.create(
            sender=self.name,
            recipient=message.sender,
            type=MessageType.HINT,
            content=hint,
            topic=topic,
        )







