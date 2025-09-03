import asyncio
import os
from typing import Optional

from utils.config import load_config
from utils.logging import setup_logging, get_logger
from models import Topic, InterviewSession
from agents.orchestrator_agent import OrchestratorAgent
from parsers import parse_resume, parse_job_description, load_topics
from dotenv import load_dotenv, find_dotenv
from tools.export import save_session_json

load_dotenv(find_dotenv(), override=False)


logger = get_logger(__name__)


def read_or_default(path: str, default_path: Optional[str]) -> str:
    if os.path.isfile(path):
        return path
    if default_path and os.path.isfile(default_path):
        return default_path
    return path


async def run_cli() -> None:
    cfg = load_config()
    setup_logging(cfg.log_level)

    resume_path = read_or_default("resume.txt", os.path.join("data", "sample_resume.txt"))
    jd_path = read_or_default("job_description.txt", os.path.join("data", "sample_job_description.txt"))
    topics_json = os.path.join("data", "sample_topics.json")

    candidate_name, resume_text = parse_resume(resume_path)
    target_role, jd_text = parse_job_description(jd_path)
    topics = load_topics(topics_json if os.path.isfile(topics_json) else None, resume_text, jd_text)

    session = InterviewSession.new(
        candidate_name=candidate_name,
        target_role=target_role,
        resume_text=resume_text,
        job_description_text=jd_text,
        topics=topics,
    )

    orch = OrchestratorAgent()
    await orch.start_session(session)

    print("Starting mock interview. Commands: /next to switch topic, /quit to end.")
    while True:
        cont = await orch.run_round(session)
        if not cont:
            break

    session.finalize()
    print("\nSession complete. Summary:")
    scores = [i.evaluation.score for i in session.interactions if i.evaluation]
    if scores:
        avg = sum(scores) / len(scores)
        print(f"Average score: {avg:.2f}/10 across {len(scores)} questions")
    else:
        print("No evaluations recorded.")
    # Display telemetry from orchestrator instance
    if orch.telemetry.timings_ms:
        print("\nTiming (aggregate):")
        for name, total in orch.telemetry.timings_ms.items():
            count = orch.telemetry.counters.get(f"{name}:count", 0)
            avg_ms = (total / count) if count else 0.0
            print(f"- {name}: {total:.0f} ms over {count} ops (~{avg_ms:.0f} ms/op)")
    # Save transcript for review
    try:
        save_session_json(session, "session_transcript.json")
        print("Saved transcript to session_transcript.json")
    except Exception:
        pass


def main():
    try:
        # Reduce event loop warnings on Windows terminals
        import sys
        if sys.platform.startswith("win"):
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[attr-defined]
            except Exception:
                pass
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        print("\nSession ended.")

if __name__ == "__main__":
    main()
