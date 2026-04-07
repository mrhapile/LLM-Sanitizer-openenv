import json
from typing import Any, Dict, Iterable, List

from grader.normalization import normalize_lines


def parse_json_score(text: str, required_keys: Iterable[str]) -> float:
    try:
        payload = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return 0.0

    if not isinstance(payload, dict):
        return 0.0

    keys = [key for key in required_keys if key]
    if not keys:
        return 1.0

    present = sum(1 for key in keys if key in payload)
    return present / len(keys)


def parse_kv_score(text: str, required_keys: Iterable[str]) -> float:
    lines = normalize_lines(text)
    if not lines:
        return 0.0

    seen = set()
    for line in lines:
        if ":" not in line:
            continue
        key, _ = line.split(":", 1)
        seen.add(key.strip())

    keys = [key for key in required_keys if key]
    if not keys:
        return 1.0

    present = sum(1 for key in keys if key in seen)
    return present / len(keys)


def structure_score(text: str, spec: Dict[str, Any]) -> float:
    structure_type = spec.get("type", "text")
    required_keys: List[str] = spec.get("required_keys", [])

    if structure_type == "json":
        return parse_json_score(text, required_keys)
    if structure_type == "kv":
        return parse_kv_score(text, required_keys)
    return 1.0 if (text or "").strip() else 0.0
