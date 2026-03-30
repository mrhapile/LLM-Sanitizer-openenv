from pydantic import BaseModel
from typing import List, Optional

class Observation(BaseModel):
    data_chunk: str
    risk_report: List[str]
    attempts_left: int

class Action(BaseModel):
    action_type: str  # redact, delete, bypass
    content: Optional[str] = ""

class Reward(BaseModel):
    score: float
