from typing import Dict, Optional

from env.models import Action, Observation, Reward
from grader.grader import ReleaseDeskGrader


SUPPORTED_ACTION_TYPES = {"redact", "rewrite", "escalate", "bypass"}


class ReleaseDeskEnv:
    def __init__(self) -> None:
        self.grader = ReleaseDeskGrader()
        self.current_index = 0
        self.steps_taken = 0
        self.max_steps = self.grader.count()
        self.remaining_escalations = 2
        self.score_total = 0.0

    def reset(self) -> Observation:
        self.current_index = 0
        self.steps_taken = 0
        self.remaining_escalations = 2
        self.score_total = 0.0
        return self._get_observation()

    def _current_task(self) -> Dict:
        return self.grader.get_task(self.current_index)

    def _get_observation(self) -> Observation:
        task = self._current_task()
        return Observation(
            document_id=task["id"],
            task_type=task["task_type"],
            task_name=task["task_name"],
            instruction=task["instruction"],
            content_format=task["content_format"],
            data_chunk=task["original_text"],
            risk_report=task["risk_report"],
            attempts_left=max(0, self.max_steps - self.steps_taken),
            documents_remaining=self.max_steps - self.current_index,
        )

    def step(self, action: Action):
        if self.current_index >= self.max_steps:
            return None, Reward(score=0.0, progress=0.0, leak_free_ratio=0.0, utility_ratio=0.0, format_ratio=0.0), True, {}

        action_type = getattr(action, "action_type", None)
        if action_type not in SUPPORTED_ACTION_TYPES:
            return self._get_observation(), Reward(score=0.0, progress=0.0, leak_free_ratio=0.0, utility_ratio=0.0, format_ratio=0.0), False, {
                "error": "invalid_action_type",
                "supported_actions": sorted(SUPPORTED_ACTION_TYPES),
            }

        task = self._current_task()
        content = getattr(action, "content", "") or ""

        if action_type == "escalate":
            if self.remaining_escalations <= 0:
                graded = {
                    "score": 0.0,
                    "progress": 0.0,
                    "leak_free_ratio": 0.0,
                    "utility_ratio": 0.0,
                    "format_ratio": 0.0,
                    "failure_reasons": ["escalation_budget_exhausted"],
                }
            else:
                self.remaining_escalations -= 1
                graded = self.grader.grade(task, action_type, content)
        else:
            graded = self.grader.grade(task, action_type, content)

        self.steps_taken += 1
        self.current_index += 1
        self.score_total += graded["score"]

        done = self.current_index >= self.max_steps
        observation: Optional[Observation] = None if done else self._get_observation()
        reward = Reward(
            score=graded["score"],
            progress=graded["progress"],
            leak_free_ratio=graded["leak_free_ratio"],
            utility_ratio=graded["utility_ratio"],
            format_ratio=graded["format_ratio"],
        )
        info = {
            "document_id": task["id"],
            "task_type": task["task_type"],
            "failure_reasons": graded["failure_reasons"],
            "remaining_escalations": self.remaining_escalations,
            "average_score": self.score_total / self.steps_taken,
        }
        return observation, reward, done, info

    def state(self) -> Dict:
        current_task = None
        if self.current_index < self.max_steps:
            current_task = self._current_task()["id"]

        return {
            "current_index": self.current_index,
            "steps_taken": self.steps_taken,
            "remaining_escalations": self.remaining_escalations,
            "current_document_id": current_task,
            "average_score": self.score_total / self.steps_taken if self.steps_taken else 0.0,
            "total_documents": self.max_steps,
        }
