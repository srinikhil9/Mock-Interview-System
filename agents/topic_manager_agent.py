from __future__ import annotations

from typing import Optional

from models import AgentMessage, MessageType, InterviewSession
from models import TopicProgress
from .base_agent import BaseAgent


class TopicManagerAgent(BaseAgent):
    async def handle(self, message: AgentMessage, session: InterviewSession) -> Optional[AgentMessage]:
        if message.type not in {MessageType.EVALUATION, MessageType.CONTROL}:
            return None

        plan = session.topic_plan
        current = plan.current()
        if current is None:
            return None

        # Decision rule: if evaluation score < 6 and depth < max_depth → ask follow-up (deepen)
        # else if rounds_on_topic >= 2 → move to next topic
        # else keep depth or move based on control message
        action = "stay"
        if message.type == MessageType.EVALUATION:
            try:
                score = float(message.metadata.get("score", 0.0))
            except Exception:
                score = 0.0
            if score < 6 and current.depth < current.topic.max_depth:
                current.depth += 1
                action = "deepen"
            elif current.rounds_on_topic >= 2:
                current.completed = True
                plan.next_topic()
                action = "next"
        else:
            # External control can force next
            if message.metadata.get("command") == "next":
                current.completed = True
                plan.next_topic()
                action = "next"

        new_current = plan.current()
        topic_name = new_current.topic.name if new_current else "Finished"
        return AgentMessage.create(
            sender=self.name,
            recipient=message.sender,
            type=MessageType.TOPIC_UPDATE,
            content=action,
            topic=topic_name,
        )


