import pytest
from env.environment import VaultSanitizerEnv
from env.models import Action

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
    env.reset()

    action1 = Action(action_type="bypass", content="bad output")
    _, reward1, _, _ = env.step(action1)

    env.reset()

    action2 = Action(action_type="redact", content="Re: Urgent\n[REDACTED], the [REDACTED], needs access.\nEmail: [REDACTED]\nAPI_KEY=[REDACTED]\n---\nConfidential")
    _, reward2, _, _ = env.step(action2)

    assert reward1.score != reward2.score

# ---------------------------
# TEST 4: DONE CONDITION
# ---------------------------
def test_done_triggers(env):
    env.reset()

    done = False

    for _ in range(20):  # more than dataset size
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
