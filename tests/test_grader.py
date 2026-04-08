from grader.grader import ESCALATION_SCORE, ReleaseDeskGrader


def test_easy_task_scores_full_credit_for_expected_output():
    grader = ReleaseDeskGrader()
    task = grader.get_task(0)
    result = grader.grade(task, "redact", task["expected_output"])

    assert result["score"] == 0.8
    assert result["leak_free_ratio"] == 1.0
    assert result["utility_ratio"] == 1.0
    assert result["policy_ratio"] == 1.0
    assert result["action_ratio"] == 1.0


def test_bypass_requires_safe_document():
    grader = ReleaseDeskGrader()
    unsafe_task = grader.get_task(0)
    safe_task = grader.get_task(1)

    unsafe_result = grader.grade(unsafe_task, "bypass", unsafe_task["original_text"])
    safe_result = grader.grade(safe_task, "bypass", safe_task["original_text"])

    assert unsafe_result["score"] == 0
    assert safe_result["score"] == 1


def test_escalation_returns_partial_credit():
    grader = ReleaseDeskGrader()
    task = grader.get_task(6)
    result = grader.grade(task, "escalate", "")

    assert result["score"] == ESCALATION_SCORE
    assert "escalated_for_review" in result["failure_reasons"]
    assert result["action_ratio"] == 0.4


def test_missing_redactions_penalize_score():
    grader = ReleaseDeskGrader()
    task = grader.get_task(6)
    partial = task["original_text"].replace("9175550188", "[REDACTED]")
    result = grader.grade(task, "rewrite", partial)

    assert result["score"] < 0.4
    assert "missed_sensitive_content" in result["failure_reasons"]
    assert "adversarial_miss" in result["failure_reasons"]


def test_task_score_bands_match_difficulty():
    grader = ReleaseDeskGrader()

    easy = grader.grade(grader.tasks_for_type("easy")[0], "redact", grader.tasks_for_type("easy")[0]["expected_output"])
    medium_task = grader.tasks_for_type("medium")[0]
    medium = grader.grade(medium_task, medium_task["preferred_action"], medium_task["expected_output"])
    hard_task = grader.tasks_for_type("hard")[0]
    hard = grader.grade(hard_task, hard_task["preferred_action"], hard_task["expected_output"])

    assert 0.6 <= easy["score"] <= 0.8
    assert 0.4 <= medium["score"] <= 0.6
    assert 0.2 <= hard["score"] <= 0.4


def test_obfuscated_secret_uses_compact_matching():
    grader = ReleaseDeskGrader()
    task = grader.get_task(5)
    partial = task["expected_output"].replace("[REDACTED]", "s k - live - WARE - 5544 - 9911", 1)
    result = grader.grade(task, "rewrite", partial)

    assert result["leak_free_ratio"] < 1.0
    assert "missed_sensitive_content" in result["failure_reasons"]


def test_suboptimal_action_is_penalized():
    grader = ReleaseDeskGrader()
    task = grader.get_task(2)
    result = grader.grade(task, "rewrite", task["expected_output"])

    assert result["action_ratio"] == 0.8
    assert "suboptimal_action" not in result["failure_reasons"]
