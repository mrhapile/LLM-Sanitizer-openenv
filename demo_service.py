import json
import os
import re
from pathlib import Path
from typing import Dict, List, Literal

from pydantic import BaseModel
from openai import OpenAI

from api_key_utils import get_api_key_env
from env.models import ActionType, ContentFormat, Reward, TaskType
from grader.grader import ReleaseDeskGrader
from grader.risk_report import build_risk_report, detect_targets
from inference import llm_agent_logic, random_agent_logic, rules_agent_logic


class DemoRunRequest(BaseModel):
    text: str
    task_type: TaskType
    policy_mode: str
    content_format: ContentFormat
    agent: Literal["random", "rules", "llm"]


class DemoCompareRequest(BaseModel):
    text: str
    task_type: TaskType
    policy_mode: str
    content_format: ContentFormat
    agents: List[Literal["random", "rules", "llm"]]


class DemoRunResponse(BaseModel):
    action_type: ActionType
    output_text: str
    notes: str
    reward: Reward
    risk_report: List[str]
    adversarial_signals: List[str]
    failure_reasons: List[str]
    detected_sensitive_types: List[str]
    preferred_action: ActionType
    reference_output: str


class DemoCompareResponse(BaseModel):
    runs: Dict[str, DemoRunResponse]


class DemoService:
    def __init__(self, manifest_path: str = "data/tasks.json") -> None:
        self.grader = ReleaseDeskGrader(manifest_path)
        self.samples = self.grader.tasks
        self.root = Path(__file__).resolve().parent

    def list_samples(self) -> List[Dict[str, str]]:
        return [
            {
                "id": task["id"],
                "task_name": task["task_name"],
                "task_type": task["task_type"],
                "policy_mode": task["policy_mode"],
                "content_format": task["content_format"],
                "text": task["original_text"],
            }
            for task in self.samples
        ]

    def featured_samples(self) -> List[Dict[str, str]]:
        featured_ids = {
            "easy_vendor_email_cleanup",
            "medium_obfuscated_kv_cleanup",
            "hard_multi_model_firewall",
        }
        featured = [sample for sample in self.list_samples() if sample["id"] in featured_ids]
        return featured or self.list_samples()[:3]

    def leaderboard(self) -> Dict:
        benchmark_path = self.root / "benchmark.json"
        if benchmark_path.exists():
            return json.loads(benchmark_path.read_text(encoding="utf-8"))

        return {
            "RandomAgent": {
                "overall": 0.225,
                "task_averages": {"easy": 0.411, "medium": 0.0, "hard": 0.263},
                "failure_counts": {"unsafe_bypass": 4},
            },
            "RulesAgent": {
                "overall": 0.971,
                "task_averages": {"easy": 1.0, "medium": 0.916, "hard": 0.998},
                "failure_counts": {"invalid_structure": 2, "policy_miss": 2},
            },
        }

    def _adversarial_signals(self, targets: List[Dict[str, str]], text: str) -> List[str]:
        signals: List[str] = []
        labels = {target["label"] for target in targets}
        if "prompt_injection" in labels:
            signals.append("prompt_injection")
        if any(target["match_mode"] == "compact" for target in targets):
            signals.append("obfuscated_secret")
        if "indirect_identifier" in labels or "person_name" in labels:
            signals.append("indirect_identifier")
        if "The only" in text:
            signals.append("unique_identity_clue")
        return sorted(set(signals))

    def _reference_sanitize(self, text: str, content_format: str, targets: List[Dict[str, str]]) -> str:
        sanitized = text
        # Replace longer phrases first so identity phrases are removed before single tokens.
        for target in sorted(targets, key=lambda item: len(item["value"]), reverse=True):
            value = target["value"]
            if target["match_mode"] == "compact":
                pattern = r"s\s*k\s*-\s*[A-Za-z0-9\s\-]{6,}"
                sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
            else:
                sanitized = sanitized.replace(value, "[REDACTED]")

        if content_format == "json":
            repaired = re.sub(r",\s*}", "}", sanitized)
            try:
                payload = json.loads(repaired)
            except json.JSONDecodeError:
                payload = {}
                for fragment in re.finditer(r'"([^"]+)"\s*:\s*"([^"]*)"', sanitized):
                    payload[fragment.group(1)] = fragment.group(2)
            return json.dumps(payload, separators=(",", ":"))

        if content_format == "kv":
            lines = []
            for line in sanitized.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                lines.append(f"{key.strip()}: {value.strip()}")
            return "\n".join(lines)

        return sanitized

    def _required_phrases(self, reference_output: str) -> List[str]:
        phrases = []
        for line in reference_output.splitlines():
            stripped = line.strip()
            if not stripped or "[REDACTED]" in stripped or len(stripped) < 14:
                continue
            phrases.append(stripped)
            if len(phrases) == 2:
                break
        return phrases

    def _preferred_action(self, content_format: str, targets: List[Dict[str, str]], adversarial_signals: List[str]) -> ActionType:
        if not targets:
            return "bypass"
        if content_format in {"json", "kv"}:
            return "rewrite"
        if adversarial_signals:
            return "rewrite"
        return "redact"

    def build_demo_task(self, request: DemoRunRequest) -> Dict:
        targets = detect_targets(request.text)
        adversarial_signals = self._adversarial_signals(targets, request.text)
        preferred_action = self._preferred_action(request.content_format, targets, adversarial_signals)
        reference_output = self._reference_sanitize(request.text, request.content_format, targets)
        required_phrases = self._required_phrases(reference_output)
        must_exclude = [target["value"] for target in targets if target["label"] in {"prompt_injection", "indirect_identifier", "person_name"}]

        structure = {"type": "text", "required_keys": []}
        if request.content_format == "json":
            required_keys: List[str] = []
            try:
                payload = json.loads(re.sub(r",\s*}", "}", request.text))
                if isinstance(payload, dict):
                    required_keys = list(payload.keys())
            except json.JSONDecodeError:
                required_keys = [match.group(1) for match in re.finditer(r'"([^"]+)"\s*:', request.text)]
            structure = {"type": "json", "required_keys": required_keys}
        elif request.content_format == "kv":
            required_keys = []
            for line in request.text.splitlines():
                if ":" in line:
                    key, _ = line.split(":", 1)
                    required_keys.append(key.strip())
            structure = {"type": "kv", "required_keys": required_keys}

        return {
            "id": "demo_input",
            "task_type": request.task_type,
            "task_name": "Live Judge Input",
            "content_format": request.content_format,
            "instruction": "Sanitize the submitted document according to the selected policy mode while preserving safe business meaning.",
            "policy_mode": request.policy_mode,
            "preferred_action": preferred_action,
            "adversarial_signals": adversarial_signals,
            "original_text": request.text,
            "expected_output": reference_output,
            "forbidden_targets": targets,
            "required_phrases": required_phrases,
            "policy_checks": {
                "must_include": required_phrases,
                "must_exclude": must_exclude,
            },
            "adversarial_checks": [
                {
                    "name": signal,
                    "forbidden_values": [target["value"] for target in targets if target["label"] in {"prompt_injection", "api_key", "indirect_identifier", "person_name"}],
                    "match_mode": "compact" if signal == "obfuscated_secret" else "literal",
                }
                for signal in adversarial_signals
            ],
            "risk_report": build_risk_report(request.text, request.content_format, targets),
            "structure": structure,
        }

    def _observation_from_task(self, task: Dict) -> Dict:
        return {
            "document_id": task["id"],
            "task_type": task["task_type"],
            "task_name": task["task_name"],
            "instruction": task["instruction"],
            "policy_mode": task["policy_mode"],
            "content_format": task["content_format"],
            "data_chunk": task["original_text"],
            "risk_report": task["risk_report"],
            "adversarial_signals": task["adversarial_signals"],
            "preferred_action": task["preferred_action"],
            "attempts_left": 1,
            "documents_remaining": 1,
            "cumulative_score": 0.0,
        }

    def _run_agent(self, request: DemoRunRequest, observation: Dict) -> Dict:
        if request.agent == "random":
            return random_agent_logic(observation)
        if request.agent == "rules":
            return rules_agent_logic(observation)

        api_key_env = get_api_key_env()
        model_name = os.getenv("MODEL_NAME", "gpt-4o-mini").strip()
        api_base_url = os.getenv("API_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).strip()
        if not api_key_env:
            raise ValueError("No API key env var found")
        _, api_key = api_key_env
        client = OpenAI(api_key=api_key, base_url=api_base_url)
        return llm_agent_logic(observation, client, model_name)

    def run(self, request: DemoRunRequest) -> DemoRunResponse:
        task = self.build_demo_task(request)
        observation = self._observation_from_task(task)
        action = self._run_agent(request, observation)
        graded = self.grader.grade(task, action["action_type"], action.get("content", ""))
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
        return DemoRunResponse(
            action_type=action["action_type"],
            output_text=action.get("content", ""),
            notes=action.get("notes", ""),
            reward=reward,
            risk_report=task["risk_report"],
            adversarial_signals=task["adversarial_signals"],
            failure_reasons=graded["failure_reasons"],
            detected_sensitive_types=graded["detected_sensitive_types"],
            preferred_action=task["preferred_action"],
            reference_output=task["expected_output"],
        )

    def compare(self, request: DemoCompareRequest) -> DemoCompareResponse:
        runs = {}
        for agent in request.agents:
            run_request = DemoRunRequest(
                text=request.text,
                task_type=request.task_type,
                policy_mode=request.policy_mode,
                content_format=request.content_format,
                agent=agent,
            )
            runs[agent] = self.run(run_request)
        return DemoCompareResponse(runs=runs)
