from __future__ import annotations

import asyncio
from typing import List

from models import InterviewSession, Topic
from agents.orchestrator_agent import OrchestratorAgent
from parsers import parse_resume, parse_job_description, load_topics


async def run_scripted_session(answers: List[str]) -> InterviewSession:
    candidate_name, resume_text = parse_resume("data/sample_resume.txt")
    target_role, jd_text = parse_job_description("data/sample_job_description.txt")
    topics = load_topics("data/sample_topics.json", resume_text, jd_text)

    session = InterviewSession.new(
        candidate_name=candidate_name,
        target_role=target_role,
        resume_text=resume_text,
        job_description_text=jd_text,
        topics=topics,
    )

    orch = OrchestratorAgent()
    await orch.start_session(session)
    for ans in answers:
        cont = await orch.run_round(session, pre_supplied_answer=ans, verbose=False)
        if not cont:
            break
    session.finalize()
    return session


def summarize(session: InterviewSession) -> dict:
    scores = [i.evaluation.score for i in session.interactions if i.evaluation]
    avg = (sum(scores) / len(scores)) if scores else 0.0
    return {
        "session_id": session.session_id,
        "num_questions": len(session.interactions),
        "avg_score": round(avg, 2),
        "topics": [i.topic for i in session.interactions],
    }


async def scenario_happy_path() -> dict:
    answers = [
        "Discussed scalable Python service using FastAPI and Postgres.",
        "Explained event-driven design and tradeoffs.",
        "Outlined consensus models in distributed systems.",
    ]
    session = await run_scripted_session(answers)
    return summarize(session)


async def scenario_next_commands() -> dict:
    answers = ["/next", "/next", "Handled cloud infra with Terraform."]
    session = await run_scripted_session(answers)
    return summarize(session)


async def scenario_empty_and_long() -> dict:
    long_answer = "A" * 5000
    answers = ["", long_answer, "/quit"]
    session = await run_scripted_session(answers)
    return summarize(session)


async def run_all() -> dict:
    return {
        "happy_path": await scenario_happy_path(),
        "next_commands": await scenario_next_commands(),
        "empty_and_long": await scenario_empty_and_long(),
    }


if __name__ == "__main__":
    import json, asyncio, sys
    try:
        if sys.platform.startswith("win"):
            # Use SelectorEventLoopPolicy to reduce proactor warnings in batch mode
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
    except Exception:
        pass
    results = asyncio.run(run_all())
    print(json.dumps(results, indent=2))


