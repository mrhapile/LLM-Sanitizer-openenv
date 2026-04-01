from grader.grader import OVER_DELETION_MIN_RATIO, VaultGrader


def _normalized_len(text):
    return len(" ".join((text or "").split()))


def _sample_text(gold_entry):
    return (
        f"Employee note for {gold_entry['name']} ({gold_entry['role']}). "
        f"Reach at {gold_entry['email']} and {gold_entry['phone']}. "
        f"Key: {gold_entry['api_key']}. "
        "Project details and non-sensitive operational context must be preserved."
    )


def test_over_deletion_returns_zero_score():
    grader = VaultGrader()
    gold = grader.get_gold(0)
    original_text = (
        f"{gold['name']} {gold['role']} {gold['email']} {gold['phone']} {gold['api_key']} "
        + ("safe " * 400)
    )

    # This keeps one repeated non-sensitive token, so pre-guard scoring would be high.
    agent_output = "safe " * 20

    assert _normalized_len(agent_output) < OVER_DELETION_MIN_RATIO * _normalized_len(original_text)

    score = grader.grade(original_text, agent_output, gold)
    assert score == 0.0


def test_partial_redaction_above_threshold_is_allowed():
    grader = VaultGrader()
    gold = grader.get_gold(0)
    original_text = _sample_text(gold)

    agent_output = (
        original_text
        .replace(gold["email"], "[REDACTED]")
        .replace(gold["phone"], "[REDACTED]")
        .replace(gold["api_key"], "[REDACTED]")
    )

    # Keep most utility; should not be auto-zeroed by length guard.
    assert _normalized_len(agent_output) >= OVER_DELETION_MIN_RATIO * _normalized_len(original_text)
    score = grader.grade(original_text, agent_output, gold)
    assert score > 0.0


def test_whitespace_padded_output_still_scores_zero():
    grader = VaultGrader()
    gold = grader.get_gold(0)
    original_text = _sample_text(gold) + (" safe" * 200)

    # Length is padded mostly by whitespace; meaningful content is still tiny.
    agent_output = (" " * 1200) + "safe" + (" " * 1200)

    assert len(agent_output) > OVER_DELETION_MIN_RATIO * len(original_text)
    assert _normalized_len(agent_output) < OVER_DELETION_MIN_RATIO * _normalized_len(original_text)

    score = grader.grade(original_text, agent_output, gold)
    assert score == 0.0
