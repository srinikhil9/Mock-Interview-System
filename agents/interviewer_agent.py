from __future__ import annotations

from typing import Optional

from models import AgentMessage, MessageType, InterviewSession
from .base_agent import BaseAgent


INTERVIEWER_SYSTEM = (
    "You are a senior technical interviewer. Ask focused, concise questions (one at a time). "
    "Adapt depth based on the current topic and depth level. Prefer behavioral evidence when relevant."
)


class InterviewerAgent(BaseAgent):
    async def handle(self, message: AgentMessage, session: InterviewSession) -> Optional[AgentMessage]:
        if message.type != MessageType.REQUEST_QUESTION:
            return None

        if message.content == "rephrase":
            original_question = message.metadata.get("question", "")
            feedback = message.metadata.get("feedback", "")
            user_prompt = (
                f"The candidate is struggling with this question: '{original_question}'\n"
                f"The feedback was: '{feedback}'\n"
                "Rephrase the question to be clearer or simpler. Focus on the core concept."
            )
            rephrased = await self.acomplete(INTERVIEWER_SYSTEM, user_prompt)
            return AgentMessage.create(
                sender=self.name,
                recipient=message.sender,
                type=MessageType.QUESTION,
                content=rephrased.strip() if rephrased else original_question,
                topic=message.topic,
            )

        topic_prog = session.topic_plan.current()
        topic_name = topic_prog.topic.name if topic_prog else "General"
        depth = topic_prog.depth if topic_prog else 0
        rounds = topic_prog.rounds_on_topic if topic_prog else 0

        # Collect recent and explicitly avoided questions to reduce repetition
        recent_qs = [i.question for i in session.interactions if i.topic == topic_name][-3:]
        avoid_qs = []
        if message.metadata and isinstance(message.metadata.get("avoid_questions"), list):
            avoid_qs = [str(x) for x in message.metadata.get("avoid_questions")][:5]
        prev_block = "\nPrevious questions on this topic:\n- " + "\n- ".join(recent_qs) if recent_qs else ""

        user = (
            f"Candidate: {session.candidate_name}\n"
            f"Target Role: {session.target_role}\n"
            f"Topic: {topic_name} (depth {depth})\n"
            f"Resume:\n{session.resume_text}\n\n"
            f"Job Description:\n{session.job_description_text}\n\n"
            f"Constraints: Do NOT repeat any previous question. Ask a new angle.{prev_block}\n"
            + ("\nAvoid these as well:\n- " + "\n- ".join(avoid_qs) if avoid_qs else "")
            + "Produce ONE question only. Be specific, grounded in resume/JD."
        )

        try:
            question = await self.acomplete(INTERVIEWER_SYSTEM, user)
            question = (question or "").strip()
            if not question.endswith("?"):
                question = question.rstrip(".") + "?"
        except Exception as e:
            self.logger.info(f"Using interviewer fallback: {e}")
            base = "Tell me about a challenging project you worked on related to "
            question = f"{base}{topic_name.lower()} and what you learned?"

        if topic_prog:
            topic_prog.rounds_on_topic = rounds + 1

        return AgentMessage.create(
            sender=self.name,
            recipient=message.sender,
            type=MessageType.QUESTION,
            content=question,
            topic=topic_name,
        )


