import pytest
from pydantic import ValidationError

from env.environment import ReleaseDeskEnv
from env.models import Action


@pytest.fixture
def env():
    return ReleaseDeskEnv()


def test_reset_returns_rich_observation(env):
    obs = env.reset()
    assert obs.document_id == "easy_ticket_redaction"
    assert obs.task_type == "easy"
    assert obs.policy_mode == "training_safe"
    assert obs.preferred_action == "redact"
    assert obs.documents_remaining == env.max_steps
    assert obs.cumulative_score == 0.0
    assert any("aria.cole@acme-retail.com" in item for item in obs.risk_report)
    assert any("sk-live-ACME99887766" in item for item in obs.risk_report)


def test_step_returns_extended_reward_and_info(env):
    obs = env.reset()
    action = Action(
        action_type="redact",
        content=obs.data_chunk
        .replace("aria.cole@acme-retail.com", "[REDACTED]")
        .replace("4155550132", "[REDACTED]")
        .replace("sk-live-ACME99887766", "[REDACTED]"),
        notes="literal cleanup",
    )
    next_obs, reward, done, info = env.step(action)

    assert reward.score == 1.0
    assert reward.policy_ratio == 1.0
    assert reward.action_ratio == 1.0
    assert reward.adversarial_ratio == 1.0
    assert info["document_id"] == "easy_ticket_redaction"
    assert info["detected_sensitive_types"] == ["api_key", "email", "phone"]
    assert done is False
    assert next_obs.document_id == "easy_safe_bypass"


def test_invalid_action_is_rejected_without_advancing(env):
    class RawAction:
        action_type = "delete"
        content = ""

    env.reset()
    state_before = env.state()
    obs, reward, done, info = env.step(RawAction())

    assert reward.score == 0.0
    assert done is False
    assert info["error"] == "invalid_action_type"
    assert env.state() == state_before
    assert obs.document_id == "easy_ticket_redaction"


def test_escalation_budget_is_enforced(env):
    env.reset()
    for _ in range(2):
        env.step(Action(action_type="escalate", content="", notes="needs review"))
    _, reward, _, info = env.step(Action(action_type="escalate", content="", notes="third escalation"))

    assert reward.score == 0.0
    assert "escalation_budget_exhausted" in info["failure_reasons"]


def test_state_tracks_task_averages_and_failures(env):
    obs = env.reset()
    env.step(
        Action(
            action_type="redact",
            content=obs.data_chunk
            .replace("aria.cole@acme-retail.com", "[REDACTED]")
            .replace("4155550132", "[REDACTED]")
            .replace("sk-live-ACME99887766", "[REDACTED]"),
        )
    )
    obs = env._get_observation()
    env.step(Action(action_type="bypass", content=obs.data_chunk))
    state = env.state()

    assert state["task_average_scores"]["easy"] == 1.0
    assert state["failure_counts"] == {}
    assert state["current_document_id"] == "easy_vendor_email_cleanup"


def test_done_after_all_documents(env):
    obs = env.reset()
    while True:
        action_type = obs.preferred_action
        content = obs.data_chunk if action_type == "bypass" else "[REDACTED]"
        obs, _, done, _ = env.step(Action(action_type=action_type, content=content))
        if done:
            break

    assert done is True
    assert obs is None


def test_model_rejects_unknown_action_type():
    with pytest.raises(ValidationError):
        Action(action_type="delete", content="")
