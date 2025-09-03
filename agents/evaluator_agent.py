from __future__ import annotations

import json
from typing import Optional, Tuple

from models import AgentMessage, MessageType, InterviewSession
from models import Evaluation
from .base_agent import BaseAgent


EVALUATOR_SYSTEM = (
    "You are a strict but fair technical interviewer. Evaluate answers concisely. "
    "Return strict JSON with keys: score (0-10), brief_feedback (<=40 words), "
    "strengths (list), improvements (list), follow_up_question (string). "
    "If score < 8, provide a specific follow_up_question. If score >= 8, follow_up_question should be empty."
)


class EvaluatorAgent(BaseAgent):
    async def handle(self, message: AgentMessage, session: InterviewSession) -> Optional[AgentMessage]:
        if message.type != MessageType.EVALUATE_RESPONSE:
            return None

        user = (
            f"Question: {message.metadata.get('question','')}\n"
            f"Answer: {message.content}\n"
            f"Topic: {message.topic}\n"
            "Respond in JSON only."
        )
        try:
            raw = await self.acomplete(EVALUATOR_SYSTEM, user)
            evaluation = self._parse_json_or_fallback(raw)
        except Exception as e:
            self.logger.info(f"Using evaluator fallback: {e}")
            evaluation = Evaluation(
                score=6.0,
                brief_feedback="Decent answer with room for specifics and tradeoffs.",
                strengths=["Clear communication"],
                improvements=["Add concrete examples", "Discuss tradeoffs"],
                follow_up_question="What were the key tradeoffs you considered?",
            )

        return AgentMessage.create(
            sender=self.name,
            recipient=message.sender,
            type=MessageType.EVALUATION,
            content=evaluation.brief_feedback,
            topic=message.topic,
            metadata={
                "score": evaluation.score,
                "strengths": evaluation.strengths,
                "improvements": evaluation.improvements,
                "follow_up_question": evaluation.follow_up_question,
            },
        )

    def _parse_json_or_fallback(self, raw: str) -> Evaluation:
        try:
            # Strip code fences or trailing text if present
            text = raw.strip()
            if text.startswith("```"):
                text = text.strip("`\n ")
                if text.startswith("json"):
                    text = text[4:]
            # Attempt to find first JSON object
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end + 1]
            data = json.loads(text)
            score = float(data.get("score", 0.0))
            brief = str(data.get("brief_feedback", ""))
            strengths = list(data.get("strengths", []))
            improvements = list(data.get("improvements", []))
            follow_up = str(data.get("follow_up_question", ""))
            return Evaluation(
                score=score,
                brief_feedback=brief,
                strengths=strengths,
                improvements=improvements,
                follow_up_question=follow_up,
            )
        except Exception:
            return Evaluation(
                score=5.0,
                brief_feedback=(raw or "Needs improvement")[0:140],
                strengths=[],
                improvements=["Provide more detail"],
                follow_up_question="Could you give a concrete example?",
            )


