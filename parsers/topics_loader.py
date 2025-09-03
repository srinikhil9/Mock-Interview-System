from __future__ import annotations

import json
from typing import List, Optional

from models import Topic


def load_topics_from_json(path: str) -> List[Topic]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    topics: List[Topic] = []
    for item in data:
        name = item.get("name")
        if not name:
            continue
        desc = item.get("description", "")
        tags = item.get("tags", [])
        max_depth = int(item.get("max_depth", 3))
        topics.append(Topic(name=name, description=desc, tags=list(tags), max_depth=max_depth))
    return topics


def infer_default_topics(resume_text: str, jd_text: str) -> List[Topic]:
    combined = (resume_text + "\n" + jd_text).lower()
    result: List[Topic] = []

    def add(name: str, desc: str, tags: list[str], depth: int = 3) -> None:
        result.append(Topic(name=name, description=desc, tags=tags, max_depth=depth))

    if "python" in combined:
        add("Python", "Language, libraries, testing", ["python"], 3)
    if "system" in combined or "design" in combined:
        add("System Design", "Architecture and tradeoffs", ["system_design"], 3)
    if "distributed" in combined:
        add("Distributed Systems", "Consistency, scaling, resilience", ["distributed"], 3)
    if "aws" in combined or "cloud" in combined or "docker" in combined:
        add("Cloud/DevOps", "AWS, Docker, infra ops", ["cloud", "devops"], 2)
    if "lead" in combined or "mentor" in combined:
        add("Leadership", "Team leadership, communication", ["leadership"], 2)

    if not result:
        result = [
            Topic("Python", "Language, libraries, testing", ["python"], 3),
            Topic("System Design", "Architecture and tradeoffs", ["system_design"], 3),
            Topic("Distributed Systems", "Consistency, scaling, resilience", ["distributed"], 3),
            Topic("Cloud/DevOps", "AWS, Docker, infra ops", ["cloud", "devops"], 2),
        ]
    return result


def load_topics(topics_path: Optional[str], resume_text: str, jd_text: str) -> List[Topic]:
    if topics_path:
        try:
            return load_topics_from_json(topics_path)
        except Exception:
            pass
    return infer_default_topics(resume_text, jd_text)







