from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Evaluation:
    score: float
    brief_feedback: str
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    follow_up_question: str = ""







