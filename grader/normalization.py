import re
from collections import Counter
from typing import Iterable, List


PLACEHOLDER = "[REDACTED]"


def normalize_whitespace(text: str) -> str:
    return " ".join((text or "").split())


def normalize_lines(text: str) -> List[str]:
    return [line.rstrip() for line in (text or "").strip().splitlines()]


def tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_\-\[\]\.]+", (text or "").lower())


def token_overlap_ratio(reference_text: str, candidate_text: str) -> float:
    reference_tokens = Counter(tokenize(reference_text))
    candidate_tokens = Counter(tokenize(candidate_text))
    if not reference_tokens:
        return 1.0

    overlap = 0
    for token, count in reference_tokens.items():
        overlap += min(count, candidate_tokens.get(token, 0))
    return overlap / sum(reference_tokens.values())


def removal_ratio(text: str, forbidden_values: Iterable[str]) -> float:
    values = [value for value in forbidden_values if value]
    if not values:
        return 1.0

    removed = sum(1 for value in values if value not in (text or ""))
    return removed / len(values)
