import json
from typing import Any, Dict, List

from grader.grading import structure_score
from grader.normalization import PLACEHOLDER, removal_ratio, token_overlap_ratio


ESCALATION_SCORE = 0.35


class ReleaseDeskGrader:
    def __init__(self, manifest_path: str = "data/tasks.json"):
        with open(manifest_path, "r", encoding="utf-8") as handle:
            self.tasks: List[Dict[str, Any]] = json.load(handle)

    def get_task(self, idx: int) -> Dict[str, Any]:
        return self.tasks[idx]

    def count(self) -> int:
        return len(self.tasks)

    def grade(self, task: Dict[str, Any], action_type: str, content: str) -> Dict[str, Any]:
        original_text = task["original_text"]
        expected_output = task["expected_output"]
        forbidden_values = task.get("forbidden_values", [])
        required_phrases = task.get("required_phrases", [])
        structure = task.get("structure", {"type": "text"})

        if action_type == "bypass":
            score = 1.0 if not forbidden_values and content == original_text else 0.0
            return {
                "score": score,
                "progress": score,
                "leak_free_ratio": score,
                "utility_ratio": 1.0 if content == original_text else 0.0,
                "format_ratio": 1.0 if content == original_text else 0.0,
                "failure_reasons": [] if score else ["unsafe_bypass"],
            }

        if action_type == "escalate":
            reasons = ["escalated_for_review"]
            return {
                "score": ESCALATION_SCORE,
                "progress": ESCALATION_SCORE,
                "leak_free_ratio": 0.0,
                "utility_ratio": 0.0,
                "format_ratio": 0.0,
                "failure_reasons": reasons,
            }

        leak_free_ratio = removal_ratio(content, forbidden_values)
        utility_ratio = token_overlap_ratio(expected_output, content)
        format_ratio = structure_score(content, structure)
        required_phrase_ratio = 1.0
        if required_phrases:
            required_phrase_ratio = sum(1 for phrase in required_phrases if phrase in content) / len(required_phrases)

        weights = {
            "easy": (0.7, 0.2, 0.1, 0.0),
            "medium": (0.45, 0.2, 0.3, 0.05),
            "hard": (0.45, 0.25, 0.15, 0.15),
        }[task["task_type"]]

        score = (
            leak_free_ratio * weights[0]
            + utility_ratio * weights[1]
            + format_ratio * weights[2]
            + required_phrase_ratio * weights[3]
        )
        score = round(max(0.0, min(1.0, score)), 6)

        failure_reasons: List[str] = []
        if leak_free_ratio < 1.0:
            failure_reasons.append("missed_sensitive_content")
        if utility_ratio < 0.75:
            failure_reasons.append("utility_loss")
        if format_ratio < 1.0 and structure.get("type") != "text":
            failure_reasons.append("invalid_structure")
        if required_phrase_ratio < 1.0:
            failure_reasons.append("context_loss")
        if PLACEHOLDER not in content and forbidden_values:
            failure_reasons.append("missing_redaction_marker")

        return {
            "score": score,
            "progress": leak_free_ratio,
            "leak_free_ratio": leak_free_ratio,
            "utility_ratio": utility_ratio,
            "format_ratio": format_ratio,
            "failure_reasons": failure_reasons,
        }
