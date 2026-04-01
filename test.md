# Test Plan and Validation Guide

This document lists all major test types for this project, with commands and expected results.

## 1. Unit Tests (Pytest)

Purpose:
- Validate environment state behavior
- Validate action schema constraints
- Validate grader anti-exploit logic

Command:
```bash
./venv/bin/pytest -q
```

Expected:
- All tests pass (currently: 12 passed)

Covered files:
- tests/test_env.py
- tests/test_grader.py

### Full list of 12 pytest test cases

From tests/test_env.py:
1. test_reset_returns_observation
2. test_step_returns_valid_response
3. test_reward_is_not_constant
4. test_done_triggers
5. test_state_updates
6. test_deterministic_behavior
7. test_action_type_rejects_unknown_value
8. test_action_type_accepts_supported_values
9. test_step_handles_invalid_action_type_gracefully

From tests/test_grader.py:
10. test_over_deletion_returns_zero_score
11. test_partial_redaction_above_threshold_is_allowed
12. test_whitespace_padded_output_still_scores_zero

Note:
- This document has 9 high-level test categories.
- Pytest executes 12 individual test functions across those categories.

---

## 2. Action Schema Consistency Tests

Purpose:
- Ensure action_type only allows supported values
- Ensure unsupported values are rejected

Validated by tests:
- test_action_type_accepts_supported_values
- test_action_type_rejects_unknown_value

Also inspect runtime schema manually:
```bash
./venv/bin/python -c "from env.models import Action; import json; print(json.dumps(Action.model_json_schema()['properties']['action_type'], indent=2))"
```

Expected:
- enum includes only: redact, delete, bypass

---

## 3. Runtime Defensive Action Handling

Purpose:
- Ensure environment handles invalid actions gracefully if validation is bypassed

Validated by test:
- test_step_handles_invalid_action_type_gracefully

Expected behavior:
- No crash
- score 0.0
- done remains false
- info contains invalid_action_type
- state is unchanged

---

## 4. Reward Exploit Prevention Tests

Purpose:
- Block reward exploitation through aggressive text deletion
- Keep valid partial redaction scoring intact

Validated by tests:
- test_over_deletion_returns_zero_score
- test_partial_redaction_above_threshold_is_allowed
- test_whitespace_padded_output_still_scores_zero

Expected:
- Over-deletion returns score 0.0
- Partial redaction can still score > 0
- Whitespace/filler padding cannot bypass deletion guard

---

## 5. API Endpoint Smoke Tests

Purpose:
- Verify OpenEnv endpoint behavior from outside interfaces

Start server:
```bash
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 7860
```

Reset:
```bash
curl -X POST http://localhost:7860/reset
```

Step:
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type":"redact","content":"Cleaned Data"}'
```

State:
```bash
curl http://localhost:7860/state
```

Expected:
- Valid JSON responses
- done progression works
- attempts_left, steps_taken, and utility_budget update correctly

---

## 6. Invalid Payload API Test

Purpose:
- Ensure no uncaught 500 errors on bad types

Command:
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type":123,"content":["bad","type"]}'
```

Expected:
- 422 validation response
- No server crash

---

## 7. Baseline Agent Continuity Test

Purpose:
- Ensure baseline evaluation script still works end-to-end

Command:
```bash
./venv/bin/python inference.py
```

Expected:
- RandomAgent and RegexAgent scores are printed
- LLMAgent runs if OPENAI_API_KEY is set, otherwise skip/fallback behavior is visible

---

## 8. Docker Build and Runtime Test

Purpose:
- Validate container build and containerized API startup

Build:
```bash
docker build -t vault-sanitizer .
```

Run:
```bash
docker run -p 7860:7860 vault-sanitizer
```

Health check:
```bash
curl -X POST http://localhost:7860/reset
```

Expected:
- Build completes successfully
- Container starts on port 7860
- API responds correctly

---

## 9. Suggested Pre-PR Checklist

Run in order:
1. ./venv/bin/pytest -q
2. ./venv/bin/python inference.py
3. docker build -t vault-sanitizer .
4. Optional API smoke tests via curl

If all pass, changes are ready for PR review.
