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
        self.per_task_type_scores = {"easy": [], "medium": [], "hard": []}
        self.failure_counts: Dict[str, int] = {}

    def reset(self) -> Observation:
        self.current_index = 0
        self.steps_taken = 0
        self.remaining_escalations = 2
        self.score_total = 0.0
        self.per_task_type_scores = {"easy": [], "medium": [], "hard": []}
        self.failure_counts = {}
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
            policy_mode=task["policy_mode"],
            content_format=task["content_format"],
            data_chunk=task["original_text"],
            risk_report=task["risk_report"],
            adversarial_signals=task.get("adversarial_signals", []),
            preferred_action=task["preferred_action"],
            attempts_left=max(0, self.max_steps - self.steps_taken),
            documents_remaining=self.max_steps - self.current_index,
            cumulative_score=round(self.score_total / self.steps_taken, 6) if self.steps_taken else 0.0,
        )

    def step(self, action: Action):
        if self.current_index >= self.max_steps:
            return None, Reward(score=0.0, progress=0.0, leak_free_ratio=0.0, utility_ratio=0.0, format_ratio=0.0, policy_ratio=0.0, action_ratio=0.0, adversarial_ratio=0.0), True, {}

        action_type = getattr(action, "action_type", None)
        if action_type not in SUPPORTED_ACTION_TYPES:
            return self._get_observation(), Reward(score=0.0, progress=0.0, leak_free_ratio=0.0, utility_ratio=0.0, format_ratio=0.0, policy_ratio=0.0, action_ratio=0.0, adversarial_ratio=0.0), False, {
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
                    "policy_ratio": 0.0,
                    "action_ratio": 0.0,
                    "adversarial_ratio": 0.0,
                    "failure_reasons": ["escalation_budget_exhausted"],
                    "detected_sensitive_types": [],
                }
            else:
                self.remaining_escalations -= 1
                graded = self.grader.grade(task, action_type, content)
        else:
            graded = self.grader.grade(task, action_type, content)

        self.steps_taken += 1
        self.current_index += 1
        self.score_total += graded["score"]
        self.per_task_type_scores[task["task_type"]].append(graded["score"])
        for failure in graded["failure_reasons"]:
            self.failure_counts[failure] = self.failure_counts.get(failure, 0) + 1

        done = self.current_index >= self.max_steps
        observation: Optional[Observation] = None if done else self._get_observation()
        reward = Reward(
            score=graded["score"],
            progress=graded["progress"],
            leak_free_ratio=graded["leak_free_ratio"],
            utility_ratio=graded["utility_ratio"],
            format_ratio=graded["format_ratio"],
            policy_ratio=graded["policy_ratio"],
            action_ratio=graded["action_ratio"],
            adversarial_ratio=graded["adversarial_ratio"],
        )
        info = {
            "document_id": task["id"],
            "task_type": task["task_type"],
            "failure_reasons": graded["failure_reasons"],
            "detected_sensitive_types": graded["detected_sensitive_types"],
            "remaining_escalations": self.remaining_escalations,
            "average_score": round(self.score_total / self.steps_taken, 6),
            "task_average_score": round(sum(self.per_task_type_scores[task["task_type"]]) / len(self.per_task_type_scores[task["task_type"]]), 6),
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
            "average_score": round(self.score_total / self.steps_taken, 6) if self.steps_taken else 0.0,
            "task_average_scores": {
                task_type: round(sum(scores) / len(scores), 6) if scores else 0.0
                for task_type, scores in self.per_task_type_scores.items()
            },
            "failure_counts": dict(sorted(self.failure_counts.items())),
            "total_documents": self.max_steps,
        }
