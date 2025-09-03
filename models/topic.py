from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Topic:
    name: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    max_depth: int = 3


@dataclass
class TopicProgress:
    topic: Topic
    depth: int = 0
    completed: bool = False
    rounds_on_topic: int = 0


@dataclass
class TopicPlan:
    topics: List[Topic]
    current_index: int = 0
    progress: List[TopicProgress] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.progress:
            self.progress = [TopicProgress(topic=t) for t in self.topics]

    def current(self) -> Optional[TopicProgress]:
        if 0 <= self.current_index < len(self.progress):
            return self.progress[self.current_index]
        return None

    def next_topic(self) -> Optional[TopicProgress]:
        self.current_index += 1
        if self.current_index >= len(self.progress):
            return None
        return self.progress[self.current_index]

    def is_finished(self) -> bool:
        return all(p.completed for p in self.progress)


