from __future__ import annotations


def parse_target_role(jd_text: str) -> str:
    lines = [l.strip() for l in jd_text.splitlines() if l.strip()]
    return lines[0] if lines else "Software Engineer"


def parse_job_description(path: str) -> tuple[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    role = parse_target_role(text)
    return role, text







