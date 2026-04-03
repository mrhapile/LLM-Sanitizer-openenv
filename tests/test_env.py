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
