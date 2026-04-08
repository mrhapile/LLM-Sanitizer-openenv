import json
from collections import Counter
from typing import Any, Dict, List

from grader.grading import structure_score
from grader.normalization import PLACEHOLDER, target_removed, token_overlap_ratio
from grader.risk_report import build_risk_report


ESCALATION_SCORE = 0.35


class ReleaseDeskGrader:
    def __init__(self, manifest_path: str = "data/tasks.json"):
        with open(manifest_path, "r", encoding="utf-8") as handle:
            self.tasks: List[Dict[str, Any]] = json.load(handle)
        for task in self.tasks:
            task["risk_report"] = build_risk_report(task["original_text"], task.get("content_format", "text"))

    def get_task(self, idx: int) -> Dict[str, Any]:
        return self.tasks[idx]

    def count(self) -> int:
        return len(self.tasks)

    def task_types(self) -> List[str]:
        return sorted({task["task_type"] for task in self.tasks})

    def tasks_for_type(self, task_type: str) -> List[Dict[str, Any]]:
        return [task for task in self.tasks if task["task_type"] == task_type]

    def _target_removal_ratio(self, content: str, targets: List[Dict[str, str]]) -> float:
        if not targets:
            return 1.0
        removed = 0
        for target in targets:
            if target_removed(content, target.get("value", ""), target.get("match_mode", "literal")):
                removed += 1
        return removed / len(targets)

    def _policy_ratio(self, content: str, task: Dict[str, Any]) -> float:
        rules = task.get("policy_checks", {})
        checks = []

        must_include = rules.get("must_include", [])
        if must_include:
            checks.append(sum(1 for phrase in must_include if phrase in content) / len(must_include))

        must_exclude = rules.get("must_exclude", [])
        if must_exclude:
            checks.append(sum(1 for phrase in must_exclude if phrase not in content) / len(must_exclude))

        if not checks:
            return 1.0
        return sum(checks) / len(checks)

    def _action_ratio(self, action_type: str, task: Dict[str, Any], leak_free_ratio: float, format_ratio: float) -> float:
        preferred = task.get("preferred_action")
        if action_type == preferred:
            return 1.0
        if preferred == "rewrite" and action_type == "redact" and format_ratio >= 0.9:
            return 0.75
        if preferred == "redact" and action_type == "rewrite" and leak_free_ratio >= 1.0:
            return 0.8
        if action_type == "escalate":
            return 0.4
        if action_type == "bypass":
            return 0.0
        return 0.35

    def _adversarial_ratio(self, content: str, task: Dict[str, Any]) -> float:
        signals = task.get("adversarial_checks", [])
        if not signals:
            return 1.0

        satisfied = 0
        for signal in signals:
            values = signal.get("forbidden_values", [])
            match_mode = signal.get("match_mode", "literal")
            if all(target_removed(content, value, match_mode) for value in values):
                satisfied += 1
        return satisfied / len(signals)

    def grade(self, task: Dict[str, Any], action_type: str, content: str) -> Dict[str, Any]:
        original_text = task["original_text"]
        expected_output = task["expected_output"]
        forbidden_targets = task.get("forbidden_targets", [])
        required_phrases = task.get("required_phrases", [])
        structure = task.get("structure", {"type": "text"})

        if action_type == "bypass":
            score = 1.0 if not forbidden_targets and content == original_text else 0.0
            return {
                "score": score,
                "progress": score,
                "leak_free_ratio": score,
                "utility_ratio": 1.0 if content == original_text else 0.0,
                "format_ratio": 1.0 if content == original_text else 0.0,
                "policy_ratio": 1.0 if content == original_text else 0.0,
                "action_ratio": 1.0 if score else 0.0,
                "adversarial_ratio": 1.0 if score else 0.0,
                "failure_reasons": [] if score else ["unsafe_bypass"],
                "detected_sensitive_types": [],
            }

        if action_type == "escalate":
            reasons = ["escalated_for_review"]
            return {
                "score": ESCALATION_SCORE,
                "progress": ESCALATION_SCORE,
                "leak_free_ratio": 0.0,
                "utility_ratio": 0.0,
                "format_ratio": 0.0,
                "policy_ratio": 0.0,
                "action_ratio": 0.4,
                "adversarial_ratio": 0.0,
                "failure_reasons": reasons,
                "detected_sensitive_types": sorted({target.get("label", "sensitive") for target in forbidden_targets}),
            }

        leak_free_ratio = self._target_removal_ratio(content, forbidden_targets)
        utility_ratio = token_overlap_ratio(expected_output, content)
        format_ratio = structure_score(content, structure)
        required_phrase_ratio = 1.0
        if required_phrases:
            required_phrase_ratio = sum(1 for phrase in required_phrases if phrase in content) / len(required_phrases)
        policy_ratio = self._policy_ratio(content, task)
        action_ratio = self._action_ratio(action_type, task, leak_free_ratio, format_ratio)
        adversarial_ratio = self._adversarial_ratio(content, task)

        weights = {
            "easy": {
                "leak": 0.5,
                "utility": 0.2,
                "format": 0.1,
                "policy": 0.1,
                "action": 0.1,
                "adversarial": 0.0,
                "context": 0.0,
            },
            "medium": {
                "leak": 0.35,
                "utility": 0.15,
                "format": 0.2,
                "policy": 0.1,
                "action": 0.1,
                "adversarial": 0.05,
                "context": 0.05,
            },
            "hard": {
                "leak": 0.28,
                "utility": 0.16,
                "format": 0.08,
                "policy": 0.16,
                "action": 0.08,
                "adversarial": 0.16,
                "context": 0.08,
            },
        }[task["task_type"]]

        score = (
            leak_free_ratio * weights["leak"]
            + utility_ratio * weights["utility"]
            + format_ratio * weights["format"]
            + policy_ratio * weights["policy"]
            + action_ratio * weights["action"]
            + adversarial_ratio * weights["adversarial"]
            + required_phrase_ratio * weights["context"]
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
        if policy_ratio < 1.0:
            failure_reasons.append("policy_miss")
        if adversarial_ratio < 1.0 and task.get("adversarial_checks"):
            failure_reasons.append("adversarial_miss")
        if action_ratio < 0.75:
            failure_reasons.append("suboptimal_action")
        if PLACEHOLDER not in content and forbidden_targets:
            failure_reasons.append("missing_redaction_marker")

        detected_sensitive_types = Counter(target.get("label", "sensitive") for target in forbidden_targets)
        return {
            "score": score,
            "progress": round((leak_free_ratio + policy_ratio + adversarial_ratio) / 3, 6),
            "leak_free_ratio": leak_free_ratio,
            "utility_ratio": utility_ratio,
            "format_ratio": format_ratio,
            "policy_ratio": policy_ratio,
            "action_ratio": action_ratio,
            "adversarial_ratio": adversarial_ratio,
            "failure_reasons": failure_reasons,
            "detected_sensitive_types": sorted(detected_sensitive_types.keys()),
        }
