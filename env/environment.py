import json
from env.models import Observation, Action, Reward

class VaultSanitizerEnv:
    def __init__(self):
        self.dataset = []
        self.gold = []
        self.current_index = 0
        self.utility_budget = 10
        self.max_steps = 3
        self.steps_taken = 0

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

        risk_report = []

        if "@" in data:
            risk_report.append("Possible email detected")
        if "sk-" in data:
            risk_report.append("Possible API key detected")

        return Observation(
            data_chunk=data,
            risk_report=risk_report,
            attempts_left=max(0, self.max_steps - self.steps_taken)
        )

    def step(self, action: Action):
        if self.current_index >= len(self.dataset) or self.utility_budget <= 0:
            return None, Reward(score=0.0), True, {}

        self.steps_taken += 1

        done = False

        # Apply action logic (basic for now)
        if action.action_type == "delete":
            self.utility_budget -= 2
        elif action.action_type == "bypass":
            self.utility_budget -= 1

        # Placeholder reward (Phase 4 will improve this)
        reward_score = 0.5

        # Move to next data chunk
        self.current_index += 1

        if self.current_index >= len(self.dataset):
            done = True

        if self.utility_budget <= 0:
            done = True

        if self.steps_taken >= self.max_steps:
            done = True

        obs = None if done else self._get_observation()

        return obs, Reward(score=reward_score), done, {}

    def state(self):
        return {
            "current_index": self.current_index,
            "utility_budget": self.utility_budget,
            "steps_taken": self.steps_taken
        }
