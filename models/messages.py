from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import uuid


def _now_ts() -> float:
    return time.time()


def _new_id() -> str:
    return uuid.uuid4().hex


class MessageType:
    REQUEST_QUESTION = "REQUEST_QUESTION"
    QUESTION = "QUESTION"
    CANDIDATE_RESPONSE = "CANDIDATE_RESPONSE"
    EVALUATE_RESPONSE = "EVALUATE_RESPONSE"
    EVALUATION = "EVALUATION"
    TOPIC_UPDATE = "TOPIC_UPDATE"
    CONTROL = "CONTROL"
    HINT = "HINT"


@dataclass
class AgentMessage:
    message_id: str
    sender: str
    recipient: str
    type: str
    content: str
    topic: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now_ts)

    @staticmethod
    def create(
        sender: str,
        recipient: str,
        type: str,
        content: str,
        topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentMessage":
        return AgentMessage(
            message_id=_new_id(),
            sender=sender,
            recipient=recipient,
            type=type,
            content=content,
            topic=topic,
            metadata=metadata or {},
        )


