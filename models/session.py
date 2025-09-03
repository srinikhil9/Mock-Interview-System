from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time
import uuid

from .topic import Topic, TopicPlan
from .evaluation import Evaluation


@dataclass
class Interaction:
    topic: str
    question: str
    answer: str
    evaluation: Optional[Evaluation] = None
    asked_at: float = field(default_factory=time.time)
    answered_at: Optional[float] = None


@dataclass
class InterviewSession:
    session_id: str
    candidate_name: str
    target_role: str
    resume_text: str
    job_description_text: str
    topic_plan: TopicPlan
    interactions: List[Interaction] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    metrics: Dict[str, float] = field(default_factory=dict)

    @staticmethod
    def new(
        candidate_name: str,
        target_role: str,
        resume_text: str,
        job_description_text: str,
        topics: List[Topic],
    ) -> "InterviewSession":
        return InterviewSession(
            session_id=uuid.uuid4().hex,
            candidate_name=candidate_name,
            target_role=target_role,
            resume_text=resume_text,
            job_description_text=job_description_text,
            topic_plan=TopicPlan(topics=topics),
        )

    def record_interaction(self, topic: str, question: str, answer: str) -> Interaction:
        interaction = Interaction(topic=topic, question=question, answer=answer)
        self.interactions.append(interaction)
        return interaction

    def finalize(self) -> None:
        self.ended_at = time.time()


