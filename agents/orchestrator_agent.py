from __future__ import annotations

import asyncio
from typing import List, Optional

from models import AgentMessage, MessageType, InterviewSession, Topic, Evaluation
from utils.logging import get_logger
from utils.telemetry import Telemetry
from .interviewer_agent import InterviewerAgent
from .topic_manager_agent import TopicManagerAgent
from .evaluator_agent import EvaluatorAgent
from .hints_agent import HintsAgent


class OrchestratorAgent:
    def __init__(self):
        self.logger = get_logger("agent.orchestrator")
        self.telemetry = Telemetry()
        self.interviewer = InterviewerAgent("interviewer", "Generates contextual interview questions")
        self.topic_manager = TopicManagerAgent("topic_manager", "Controls topic flow and depth")
        self.evaluator = EvaluatorAgent("evaluator", "Evaluates responses and provides feedback")
        self.hints = HintsAgent("hints", "Provides a short hint before follow-ups")

    async def start_session(self, session: InterviewSession) -> None:
        self.logger.info(
            f"Starting session {session.session_id} for {session.candidate_name} targeting {session.target_role}"
        )
        self.telemetry.incr("sessions_started")

    async def run_round(
        self,
        session: InterviewSession,
        pre_supplied_answer: Optional[str] = None,
        verbose: bool = True,
    ) -> bool:
        if session.topic_plan.is_finished() or session.topic_plan.current() is None:
            return False

        current = session.topic_plan.current()
        topic_name = current.topic.name

        # Suggest avoiding the last few questions (any topic) to improve variety
        avoid_questions = [i.question for i in session.interactions][-5:]

        req = AgentMessage.create(
            sender="orchestrator",
            recipient="interviewer",
            type=MessageType.REQUEST_QUESTION,
            content="next",
            topic=topic_name,
            metadata={"avoid_questions": avoid_questions} if avoid_questions else {},
        )
        with self.telemetry.timer("question_gen_ms"):
            q_msg = await self.interviewer.handle(req, session)
        if not q_msg:
            return False

        question = q_msg.content
        if verbose:
            print(f"\n[Topic: {topic_name} | Depth: {current.depth}]\nQ: {question}")
            print("Type '/next' to switch topic, or '/quit' to end.")
        if pre_supplied_answer is not None:
            answer = pre_supplied_answer
            if verbose:
                print(f"Your answer: {answer}")
        else:
            try:
                answer = input("Your answer: ")
            except (KeyboardInterrupt, EOFError):
                return False

        if answer.strip().lower() in {"/quit", "quit"}:
            return False

        if answer.strip().lower() in {"/next", "/skip", "next", "skip"}:
            ctrl = AgentMessage.create(
                sender="orchestrator",
                recipient="topic_manager",
                type=MessageType.CONTROL,
                content="control",
                topic=topic_name,
                metadata={"command": "next"},
            )
            topic_update = await self.topic_manager.handle(ctrl, session)
            if topic_update and topic_update.content == "next":
                new_current = session.topic_plan.current()
                if new_current is None:
                    return False
                if verbose:
                    print(f"-- Switching to topic: {new_current.topic.name} --")
            return True
        interaction = session.record_interaction(topic_name, question, answer)
        interaction.answered_at = asyncio.get_event_loop().time()

        # Evaluate or handle empty answer with a manual low score
        if not answer.strip():
            e_msg = AgentMessage.create(
                sender="evaluator",
                recipient="orchestrator",
                type=MessageType.EVALUATION,
                content="No answer provided.",
                topic=topic_name,
                metadata={
                    "score": 1.0,
                    "strengths": [],
                    "improvements": ["Provide a specific, detailed answer"],
                    "follow_up_question": "Could you share a concrete example, including metrics and tradeoffs?",
                },
            )
            eval_req = None  # type: ignore[assignment]
        else:
            eval_req = AgentMessage.create(
                sender="orchestrator",
                recipient="evaluator",
                type=MessageType.EVALUATE_RESPONSE,
                content=answer,
                topic=topic_name,
                metadata={"question": question},
            )
            with self.telemetry.timer("evaluation_ms"):
                e_msg = await self.evaluator.handle(eval_req, session)
        if e_msg:
            score = float(e_msg.metadata.get("score", 0))
            if verbose:
                print(f"Feedback: {e_msg.content} (score: {score:.1f}/10)")
            follow = e_msg.metadata.get("follow_up_question", "")
            if follow and verbose:
                print(f"Follow-up: {follow}")
            interaction.evaluation = Evaluation(
                score=score,
                brief_feedback=e_msg.content,
                strengths=list(e_msg.metadata.get("strengths", [])),
                improvements=list(e_msg.metadata.get("improvements", [])),
                follow_up_question=str(e_msg.metadata.get("follow_up_question", "")),
            )
            # Ask HintsAgent for a nudge before follow-up
            try:
                hint_msg = await self.hints.handle(e_msg, session)
                if hint_msg and verbose and hint_msg.content:
                    print(f"Hint: {hint_msg.content}")
            except Exception:
                pass

            # If score is low, consider rephrasing instead of just following up
            if score < 4.0:
                rephrase_req = AgentMessage.create(
                    sender="orchestrator",
                    recipient="interviewer",
                    type=MessageType.REQUEST_QUESTION,
                    content="rephrase",
                    topic=topic_name,
                    metadata={"question": question, "feedback": e_msg.content},
                )
                rephrased_msg = await self.interviewer.handle(rephrase_req, session)
                if rephrased_msg:
                    e_msg.metadata["follow_up_question"] = rephrased_msg.content

        # If there is a follow-up question, handle it immediately in the same round (interactive mode only)
        final_eval_msg = e_msg
        # Loop through follow-ups until satisfactory (score >= 8) or no follow-up provided
        if e_msg and pre_supplied_answer is None:
            follow_ups_done = 0
            while True:
                fu_prompt = str(final_eval_msg.metadata.get("follow_up_question")) if final_eval_msg else ""
                if not fu_prompt:
                    break
                try:
                    fu_answer = input("Your follow-up answer: ") if verbose else ""
                except (KeyboardInterrupt, EOFError):
                    return False

                # Handle control commands at follow-up stage
                cmd = fu_answer.strip().lower()
                if cmd in {"/quit", "quit"}:
                    return False
                if cmd in {"/next", "/skip", "next", "skip"}:
                    ctrl = AgentMessage.create(
                        sender="orchestrator",
                        recipient="topic_manager",
                        type=MessageType.CONTROL,
                        content="control",
                        topic=topic_name,
                        metadata={"command": "next"},
                    )
                    topic_update = await self.topic_manager.handle(ctrl, session)
                    if topic_update and topic_update.content == "next" and verbose:
                        new_current = session.topic_plan.current()
                        if new_current is not None:
                            print(f"-- Switching to topic: {new_current.topic.name} --")
                    return True

                if not fu_answer.strip():
                    fu_eval_msg = AgentMessage.create(
                        sender="evaluator",
                        recipient="orchestrator",
                        type=MessageType.EVALUATION,
                        content="No answer provided.",
                        topic=topic_name,
                        metadata={
                            "score": 1.0,
                            "strengths": [],
                            "improvements": ["Provide a specific, detailed answer"],
                            "follow_up_question": fu_prompt,
                        },
                    )
                else:
                    fu_interaction = session.record_interaction(topic_name, fu_prompt, fu_answer)
                    fu_interaction.answered_at = asyncio.get_event_loop().time()
                    fu_eval_req = AgentMessage.create(
                        sender="orchestrator",
                        recipient="evaluator",
                        type=MessageType.EVALUATE_RESPONSE,
                        content=fu_answer,
                        topic=topic_name,
                        metadata={"question": fu_prompt},
                    )
                    with self.telemetry.timer("evaluation_ms"):
                        fu_eval_msg = await self.evaluator.handle(fu_eval_req, session)

                follow_ups_done += 1
                if fu_eval_msg:
                    final_eval_msg = fu_eval_msg
                    fu_score = float(fu_eval_msg.metadata.get("score", 0))
                    if verbose:
                        print(f"Feedback: {fu_eval_msg.content} (score: {fu_score:.1f}/10)")
                    # Continue loop only if score < 8 and a follow-up is provided
                    if fu_score >= 8 or not fu_eval_msg.metadata.get("follow_up_question") or follow_ups_done >= 3:
                        break

        topic_update = await self.topic_manager.handle(final_eval_msg or eval_req, session)
        if topic_update and topic_update.content == "next":
            new_current = session.topic_plan.current()
            if new_current is None:
                return False
            if verbose:
                print(f"-- Switching to topic: {new_current.topic.name} --")
        elif topic_update and topic_update.content == "deepen":
            if verbose:
                print("-- Going deeper on the same topic --")
        self.telemetry.incr("rounds_completed")

        return True


