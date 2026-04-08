from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_serializer


TaskType = Literal["easy", "medium", "hard"]
ContentFormat = Literal["email", "ticket", "json", "kv", "memo", "report"]
ActionType = Literal["redact", "rewrite", "escalate", "bypass"]


class Observation(BaseModel):
    document_id: str
    task_type: TaskType
    task_name: str
    instruction: str
    policy_mode: str
    content_format: ContentFormat
    data_chunk: str
    risk_report: List[str]
    adversarial_signals: List[str]
    preferred_action: ActionType
    attempts_left: int
    documents_remaining: int
    cumulative_score: float

    @field_serializer("cumulative_score")
    def serialize_cumulative_score(self, value: float):
        if value in {0, 1, 0.0, 1.0}:
            return int(value)
        return value


class Action(BaseModel):
    action_type: ActionType
    content: Optional[str] = ""
    notes: str = Field(default="", max_length=280)


class Reward(BaseModel):
    score: float
    progress: float
    leak_free_ratio: float
    utility_ratio: float
    format_ratio: float
    policy_ratio: float
    action_ratio: float
    adversarial_ratio: float

    @field_serializer(
        "score",
        "progress",
        "leak_free_ratio",
        "utility_ratio",
        "format_ratio",
        "policy_ratio",
        "action_ratio",
        "adversarial_ratio",
    )
    def serialize_reward_value(self, value: float):
        if value in {0, 1, 0.0, 1.0}:
            return int(value)
        return value


class ResetRequest(BaseModel):
    task_name: Optional[str] = None
