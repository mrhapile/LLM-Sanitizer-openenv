import pytest
from env.environment import VaultSanitizerEnv
from env.models import Action
from pydantic import ValidationError

@pytest.fixture
def env():
    return VaultSanitizerEnv()

# ---------------------------
# TEST 1: RESET
# ---------------------------
def test_reset_returns_observation(env):
    obs = env.reset()

    assert obs is not None
    assert hasattr(obs, "data_chunk")
    assert hasattr(obs, "risk_report")
    assert hasattr(obs, "attempts_left")


def test_risk_report_detects_email_and_api_key_via_regex(env):
    env.dataset = [
        {"input": "Email me at alice@example.com for details."},
        {"input": "Use key sk-1234567890abcdef1234 for access."},
        {"input": "Nothing sensitive here."},
    ]
    env.current_index = 0

    obs1 = env.reset()
    assert any("Email detected:" in item for item in obs1.risk_report)

    env.current_index = 1
    obs2 = env._get_observation()
    assert any("API key detected:" in item for item in obs2.risk_report)

    env.current_index = 2
    obs3 = env._get_observation()
    assert obs3.risk_report == []


def test_risk_report_varies_per_sample(env):
    env.dataset = [
        {"input": "Email alice@example.com is here."},
        {"input": "API key sk-1234567890abcdef1234 is here."},
    ]
    env.current_index = 0

    first = env._get_observation().risk_report
    env.current_index = 1
    second = env._get_observation().risk_report

    assert first != second

# ---------------------------
# TEST 2: STEP BASIC
# ---------------------------
def test_step_returns_valid_response(env):
    env.reset()

    action = Action(action_type="bypass", content="test")

    obs, reward, done, info = env.step(action)

    assert reward is not None
    assert hasattr(reward, "score")
    assert isinstance(done, bool)


def test_bypass_on_sensitive_chunk_is_heavily_penalized(env):
    env.reset()

    action = Action(action_type="bypass", content="")
    _, reward, _, _ = env.step(action)

    assert reward.score == -1.0

# ---------------------------
# TEST 3: REWARD CHANGES
# ---------------------------
def test_reward_is_not_constant(env):
    obs = env.reset()

    action1 = Action(action_type="bypass", content="bad output")
    _, reward1, _, _ = env.step(action1)

    env.reset()

    # Dynamically build a proper redaction from the first chunk's gold data
    gold = env.grader.get_gold(0)
    redacted = obs.data_chunk
    for field in ["email", "phone", "api_key", "name", "role"]:
        if gold[field] in redacted:
            redacted = redacted.replace(gold[field], "[REDACTED]")

    action2 = Action(action_type="redact", content=redacted)
    _, reward2, _, _ = env.step(action2)

    assert reward1.score != reward2.score

# ---------------------------
# TEST 4: DONE CONDITION
# ---------------------------
def test_done_triggers(env):
    env.reset()

    done = False

    for _ in range(220):  # more than dataset size
        action = Action(action_type="bypass", content="test")
        _, _, done, _ = env.step(action)
        if done:
            break

    assert done is True

# ---------------------------
# TEST 5: STATE API
# ---------------------------
def test_state_updates(env):
    env.reset()

    action = Action(action_type="bypass", content="test")
    env.step(action)

    state = env.state()

    assert "current_index" in state
    assert "utility_budget" in state
    assert "steps_taken" in state

# ---------------------------
# TEST 6: DETERMINISM
# ---------------------------
def test_deterministic_behavior(env):
    env.reset()

    action = Action(action_type="bypass", content="same input")

    _, reward1, _, _ = env.step(action)

    env.reset()

    _, reward2, _, _ = env.step(action)

    assert reward1.score == reward2.score


def test_action_type_rejects_unknown_value():
    with pytest.raises(ValidationError) as exc_info:
        Action(action_type="mask", content="test")

    errors = exc_info.value.errors()
    assert any("action_type" in err.get("loc", []) for err in errors)
    assert "mask" in str(exc_info.value)


def test_action_type_accepts_supported_values():
    for action_type in ["redact", "delete", "bypass"]:
        action = Action(action_type=action_type, content="test")
        assert action.action_type == action_type


def test_step_handles_invalid_action_type_gracefully(env):
    class RawAction:
        action_type = "mask"
        content = "test"

    env.reset()
    state_before = env.state().copy()

    obs, reward, done, info = env.step(RawAction())

    assert obs is not None
    assert reward.score == 0.0
    assert done is False
    assert info.get("error") == "invalid_action_type"
    assert info.get("supported_actions") == ["bypass", "delete", "redact"]
    assert env.state() == state_before
