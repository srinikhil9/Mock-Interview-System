from __future__ import annotations

import json
from typing import Any

from models import InterviewSession, Interaction


def session_to_dict(session: InterviewSession) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "candidate": session.candidate_name,
        "target_role": session.target_role,
        "topics": [p.topic.name for p in session.topic_plan.progress],
        "interactions": [
            {
                "topic": i.topic,
                "question": i.question,
                "answer": i.answer,
                "evaluation": (
                    {
                        "score": i.evaluation.score,
                        "feedback": i.evaluation.brief_feedback,
                        "strengths": i.evaluation.strengths,
                        "improvements": i.evaluation.improvements,
                        "follow_up": i.evaluation.follow_up_question,
                    }
                    if i.evaluation
                    else None
                ),
            }
            for i in session.interactions
        ],
    }


def save_session_json(session: InterviewSession, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session_to_dict(session), f, indent=2)







