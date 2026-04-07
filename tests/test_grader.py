from grader.grader import ESCALATION_SCORE, ReleaseDeskGrader


def test_easy_task_scores_full_credit_for_expected_output():
    grader = ReleaseDeskGrader()
    task = grader.get_task(0)
    result = grader.grade(task, "redact", task["expected_output"])

    assert result["score"] == 1.0
    assert result["leak_free_ratio"] == 1.0
    assert result["utility_ratio"] == 1.0


def test_bypass_requires_safe_document():
    grader = ReleaseDeskGrader()
    unsafe_task = grader.get_task(0)
    safe_task = grader.get_task(1)

    unsafe_result = grader.grade(unsafe_task, "bypass", unsafe_task["original_text"])
    safe_result = grader.grade(safe_task, "bypass", safe_task["original_text"])

    assert unsafe_result["score"] == 0.0
    assert safe_result["score"] == 1.0


def test_escalation_returns_partial_credit():
    grader = ReleaseDeskGrader()
    task = grader.get_task(4)
    result = grader.grade(task, "escalate", "")

    assert result["score"] == ESCALATION_SCORE
    assert "escalated_for_review" in result["failure_reasons"]


def test_missing_redactions_penalize_score():
    grader = ReleaseDeskGrader()
    task = grader.get_task(4)
    partial = task["original_text"].replace("9175550188", "[REDACTED]")
    result = grader.grade(task, "rewrite", partial)

    assert result["score"] < 0.7
    assert "missed_sensitive_content" in result["failure_reasons"]
