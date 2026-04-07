import pytest
from pydantic import ValidationError

from env.environment import ReleaseDeskEnv
from env.models import Action


@pytest.fixture
def env():
    return ReleaseDeskEnv()


def test_reset_returns_first_document(env):
    obs = env.reset()
    assert obs.document_id == "easy_ticket_redaction"
    assert obs.task_type == "easy"
    assert obs.documents_remaining == env.max_steps


def test_step_advances_state(env):
    obs = env.reset()
    action = Action(action_type="redact", content=obs.data_chunk.replace("aria.cole@acme-retail.com", "[REDACTED]").replace("4155550132", "[REDACTED]").replace("sk-live-ACME99887766", "[REDACTED]"))
    next_obs, reward, done, info = env.step(action)

    assert reward.score > 0.8
    assert done is False
    assert next_obs.document_id == "easy_safe_bypass"
    assert info["document_id"] == "easy_ticket_redaction"


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


def test_done_after_all_documents(env):
    obs = env.reset()
    while True:
        action_type = "bypass" if "No obvious high-risk markers detected" in obs.risk_report else "rewrite"
        obs, _, done, _ = env.step(Action(action_type=action_type, content="[REDACTED]"))
        if done:
            break

    assert done is True
    assert obs is None


def test_model_rejects_unknown_action_type():
    with pytest.raises(ValidationError):
        Action(action_type="delete", content="")
