from __future__ import annotations

from typing import Tuple


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def parse_candidate_name(resume_text: str) -> str:
    for line in resume_text.splitlines():
        line = line.strip()
        if line:
            return line
    return "Candidate"


def parse_resume(resume_path: str) -> tuple[str, str]:
    text = read_text_file(resume_path)
    name = parse_candidate_name(text)
    return name, text







