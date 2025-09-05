from __future__ import annotations

import os
from typing import Dict, Optional, List
import time

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils.logging import setup_logging
from parsers import parse_resume, parse_job_description, load_topics
from models import AgentMessage, MessageType, InterviewSession
from agents.orchestrator_agent import OrchestratorAgent
from tools.export import session_to_dict


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_logging("INFO")
app.state.start_time = time.time()


class CreateSessionResp(BaseModel):
    session_id: str
    candidate_name: str
    target_role: str
    topics: List[str]


class NextReq(BaseModel):
    session_id: str


class NextResp(BaseModel):
    topic: str
    depth: int
    question: str


class AnswerReq(BaseModel):
    session_id: str
    answer: str


class AnswerResp(BaseModel):
    topic: str
    score: float
    brief_feedback: str
    strengths: List[str]
    improvements: List[str]
    follow_up_question: str
    hint: Optional[str] = None
    topic_action: str  # "stay" | "deepen" | "next"
    current_topic: str


class HealthResp(BaseModel):
    status: str
    uptime_seconds: float
    sessions: int


class VersionResp(BaseModel):
    version: str
    api: str


class SessionSummaryResp(BaseModel):
    session_id: str
    num_questions: int
    avg_score: float
    current_topic: str
    finished: bool


# session_id -> {"session": InterviewSession, "orch": OrchestratorAgent, "pending_question": Optional[str]}
SESSIONS: Dict[str, Dict[str, object]] = {}


def _ensure_session(sid: str) -> Dict[str, object]:
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s


@app.get("/health", response_model=HealthResp)
async def health() -> HealthResp:
    return HealthResp(
        status="ok",
        uptime_seconds=round(time.time() - app.state.start_time, 3),
        sessions=len(SESSIONS),
    )


@app.get("/version", response_model=VersionResp)
async def version() -> VersionResp:
    # Lightweight static version; adjust as needed
    return VersionResp(version="0.1.0", api="v1")


@app.post("/api/session", response_model=CreateSessionResp)
async def create_session(
    resume: UploadFile = File(...),
    jd: UploadFile = File(...)
):
    
    resume_path = os.path.join("data", resume.filename)
    with open(resume_path, "wb") as f:
        f.write(await resume.read())

    jd_path = os.path.join("data", jd.filename)
    with open(jd_path, "wb") as f:
        f.write(await jd.read())
        
    candidate_name, resume_text = parse_resume(resume_path)
    target_role, jd_text = parse_job_description(jd_path)
    topics_path = os.path.join("data", "sample_topics.json")
    topics = load_topics(topics_path if os.path.isfile(topics_path) else None, resume_text, jd_text)

    session = InterviewSession.new(
        candidate_name=candidate_name,
        target_role=target_role,
        resume_text=resume_text,
        job_description_text=jd_text,
        topics=topics,
    )
    orch = OrchestratorAgent()
    await orch.start_session(session)
    SESSIONS[session.session_id] = {"session": session, "orch": orch, "pending_question": None}

    return CreateSessionResp(
        session_id=session.session_id,
        candidate_name=candidate_name,
        target_role=target_role,
        topics=[t.name for t in topics],
    )


@app.post("/api/next", response_model=NextResp)
async def next_question(req: NextReq):
    store = _ensure_session(req.session_id)
    session: InterviewSession = store["session"]  # type: ignore[assignment]
    orch: OrchestratorAgent = store["orch"]  # type: ignore[assignment]

    cur = session.topic_plan.current()
    if cur is None or session.topic_plan.is_finished():
        raise HTTPException(status_code=400, detail="no more topics")

    topic_name = cur.topic.name
    msg = AgentMessage.create(
        sender="orchestrator",
        recipient="interviewer",
        type=MessageType.REQUEST_QUESTION,
        content="next",
        topic=topic_name,
    )
    q_msg = await orch.interviewer.handle(msg, session)
    if not q_msg:
        raise HTTPException(status_code=500, detail="failed to produce question")
    question = q_msg.content
    store["pending_question"] = question
    return NextResp(topic=topic_name, depth=cur.depth, question=question)


@app.post("/api/answer", response_model=AnswerResp)
async def submit_answer(req: AnswerReq):
    store = _ensure_session(req.session_id)
    session: InterviewSession = store["session"]  # type: ignore[assignment]
    orch: OrchestratorAgent = store["orch"]  # type: ignore[assignment]
    pending_q: Optional[str] = store.get("pending_question")  # type: ignore[assignment]

    cur = session.topic_plan.current()
    if cur is None:
        raise HTTPException(status_code=400, detail="session finished")

    cmd = req.answer.strip().lower()
    if cmd in {"/quit", "quit"}:
        session.finalize()
        return AnswerResp(
            topic=cur.topic.name,
            score=0.0,
            brief_feedback="Session ended.",
            strengths=[],
            improvements=[],
            follow_up_question="",
            topic_action="next",
            current_topic="Finished",
        )

    if cmd in {"/next", "/skip", "next", "skip"}:
        ctrl = AgentMessage.create(
            sender="orchestrator",
            recipient="topic_manager",
            type=MessageType.CONTROL,
            content="control",
            topic=cur.topic.name,
            metadata={"command": "next"},
        )
        update = await orch.topic_manager.handle(ctrl, session)
        new_cur = session.topic_plan.current()
        return AnswerResp(
            topic=cur.topic.name,
            score=0.0,
            brief_feedback="Topic switched.",
            strengths=[],
            improvements=[],
            follow_up_question="",
            topic_action=update.content if update else "next",
            current_topic=(new_cur.topic.name if new_cur else "Finished"),
        )

    question = pending_q or "(unspecified)"
    interaction = session.record_interaction(cur.topic.name, question, req.answer)

    eval_req = AgentMessage.create(
        sender="orchestrator",
        recipient="evaluator",
        type=MessageType.EVALUATE_RESPONSE,
        content=req.answer,
        topic=cur.topic.name,
        metadata={"question": question},
    )
    e_msg = await orch.evaluator.handle(eval_req, session)
    follow = str(e_msg.metadata.get("follow_up_question", "")) if e_msg else ""
    score = float(e_msg.metadata.get("score", 0.0)) if e_msg else 0.0

    if e_msg:
        from models import Evaluation
        interaction.evaluation = Evaluation(
            score=score,
            brief_feedback=e_msg.content,
            strengths=list(e_msg.metadata.get("strengths", [])),
            improvements=list(e_msg.metadata.get("improvements", [])),
            follow_up_question=follow,
        )

    hint_msg = await orch.hints.handle(e_msg, session) if e_msg else None
    hint_text = hint_msg.content if hint_msg and hint_msg.content else None

    update = await orch.topic_manager.handle(e_msg, session) if e_msg else None
    action = update.content if update else "stay"
    new_cur = session.topic_plan.current()

    store["pending_question"] = follow if follow else None

    return AnswerResp(
        topic=cur.topic.name,
        score=score,
        brief_feedback=(e_msg.content if e_msg else ""),
        strengths=list(e_msg.metadata.get("strengths", [])) if e_msg else [],
        improvements=list(e_msg.metadata.get("improvements", [])) if e_msg else [],
        follow_up_question=follow,
        hint=hint_text,
        topic_action=action,
        current_topic=(new_cur.topic.name if new_cur else "Finished"),
    )


@app.get("/api/export/{session_id}")
async def export_session(session_id: str):
    store = _ensure_session(session_id)
    session: InterviewSession = store["session"]  # type: ignore[assignment]
    return session_to_dict(session)


@app.get("/api/sessions/{session_id}", response_model=SessionSummaryResp)
async def get_session_summary(session_id: str) -> SessionSummaryResp:
    store = _ensure_session(session_id)
    session: InterviewSession = store["session"]  # type: ignore[assignment]
    scores = [i.evaluation.score for i in session.interactions if i.evaluation]
    avg = (sum(scores) / len(scores)) if scores else 0.0
    cur = session.topic_plan.current()
    return SessionSummaryResp(
        session_id=session.session_id,
        num_questions=len(session.interactions),
        avg_score=round(avg, 2),
        current_topic=(cur.topic.name if cur else "Finished"),
        finished=(session.ended_at is not None or session.topic_plan.is_finished()),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


app.mount("/", StaticFiles(directory="static", html=True), name="static")


