import json
import re
from env.models import Observation, Action, Reward
from grader.grader import VaultGrader


SUPPORTED_ACTION_TYPES = {"redact", "delete", "bypass"}

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
API_KEY_REGEXES = [
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bgsk-[A-Za-z0-9]{20,}\b"),
]


def _mask_value(value):
    if len(value) <= 8:
        return "[REDACTED]"
    return f"{value[:4]}...{value[-4:]}"


def _detect_risk_report(text):
    risk_report = []

    email_matches = EMAIL_REGEX.findall(text)
    if email_matches:
        masked_matches = ", ".join(_mask_value(match) for match in email_matches)
        risk_report.append(f"Email detected: {masked_matches}")

    api_key_matches = []
    for pattern in API_KEY_REGEXES:
        api_key_matches.extend(pattern.findall(text))
    if api_key_matches:
        masked_matches = ", ".join(_mask_value(match) for match in api_key_matches)
        risk_report.append(f"API key detected: {masked_matches}")

    return risk_report


class VaultSanitizerEnv:
    def __init__(self):
        self.dataset = []
        self.gold = []
        self.current_index = 0
        self.utility_budget = 10
        self.max_steps = 210
        self.steps_taken = 0
        self.grader = VaultGrader()

        self.load_data()

    def load_data(self):
        with open("data/dataset.jsonl") as f:
            self.dataset = [json.loads(line) for line in f]

        with open("data/gold_manifest.json") as f:
            self.gold = json.load(f)

    def reset(self):
        self.current_index = 0
        self.utility_budget = 10
        self.steps_taken = 0

        return self._get_observation()

    def _get_observation(self):
        data = self.dataset[self.current_index]["input"]

        return Observation(
            data_chunk=data,
            risk_report=_detect_risk_report(data),
            attempts_left=max(0, self.max_steps - self.steps_taken)
        )

    def step(self, action: Action):
        # Halt immediately if any terminal condition has already been reached.
        if (
            self.current_index >= len(self.dataset)
            or self.utility_budget <= 0
            or self.steps_taken >= self.max_steps
        ):
            return None, Reward(score=0.0), True, {}

        action_type = getattr(action, "action_type", None)
        if action_type not in SUPPORTED_ACTION_TYPES:
            return self._get_observation(), Reward(score=0.0), False, {
                "error": "invalid_action_type",
                "supported_actions": sorted(SUPPORTED_ACTION_TYPES),
            }

        self.steps_taken += 1

        done = False

        # Apply action logic (basic for now)
        if action_type == "delete":
            self.utility_budget -= 2
        elif action_type == "bypass":
            self.utility_budget -= 1

        # Get gold truth for current sample
        gold_entry = self.grader.get_gold(self.current_index)

        original_text = self.dataset[self.current_index]["input"]
        agent_output = getattr(action, "content", "") or ""

        score = self.grader.grade(
            original_text=original_text,
            agent_output=agent_output,
            gold_entry=gold_entry,
            action_type=action_type,
        )

        # Move to next data chunk
        self.current_index += 1

        if self.current_index >= len(self.dataset):
            done = True

        if self.utility_budget <= 0:
            done = True

        if self.steps_taken >= self.max_steps:
            done = True

        obs = None if done else self._get_observation()

        return obs, Reward(score=score), done, {}

    def state(self):
        return {
            "current_index": self.current_index,
            "utility_budget": self.utility_budget,
            "steps_taken": self.steps_taken
        }
