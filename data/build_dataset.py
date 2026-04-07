import json
from pathlib import Path


TASKS_PATH = Path(__file__).resolve().parent / "tasks.json"

REQUIRED_FIELDS = {
    "id",
    "task_type",
    "task_name",
    "content_format",
    "instruction",
    "policy_mode",
    "preferred_action",
    "original_text",
    "expected_output",
    "forbidden_targets",
    "required_phrases",
    "policy_checks",
    "adversarial_checks",
    "risk_report",
    "structure",
}


def validate_tasks(tasks):
    seen_ids = set()
    for task in tasks:
        missing = REQUIRED_FIELDS - set(task.keys())
        if missing:
            raise ValueError(f"Task {task.get('id', '<unknown>')} missing fields: {sorted(missing)}")
        if task["id"] in seen_ids:
            raise ValueError(f"Duplicate task id: {task['id']}")
        seen_ids.add(task["id"])


def main() -> None:
    tasks = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    validate_tasks(tasks)
    TASKS_PATH.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")
    print(f"Validated and normalized {len(tasks)} tasks in {TASKS_PATH}")


if __name__ == "__main__":
    main()
