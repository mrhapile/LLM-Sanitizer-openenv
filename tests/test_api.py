from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_exposes_environment_metadata():
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["environment"] == "release_desk"
    assert payload["tasks"] == ["easy", "medium", "hard"]
    assert "rewrite" in payload["actions"]


def test_healthcheck_endpoint():
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["documents"] > 0


def test_demo_samples_endpoint():
    response = client.get("/demo/samples")
    assert response.status_code == 200
    payload = response.json()
    assert payload["samples"]
    assert "text" in payload["samples"][0]


def test_judge_page_and_featured_endpoints():
    assert client.get("/judge").status_code == 200
    featured = client.get("/demo/featured")
    assert featured.status_code == 200
    assert len(featured.json()["samples"]) >= 1


def test_demo_leaderboard_endpoint():
    response = client.get("/demo/leaderboard")
    assert response.status_code == 200
    payload = response.json()["leaderboard"]
    assert "RulesAgent" in payload


def test_demo_run_endpoint_with_rules_agent():
    response = client.post(
        "/demo/run",
        json={
            "text": "Contact remy.lopez@supplyline.net at 3125550109 with key sk-session-SUPPLY7788",
            "task_type": "easy",
            "policy_mode": "external_sharing",
            "content_format": "email",
            "agent": "rules",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["action_type"] in {"redact", "rewrite"}
    assert "[REDACTED]" in payload["output_text"]
    assert payload["reward"]["leak_free_ratio"] == 1.0


def test_demo_run_risk_report_reflects_sample_content():
    response = client.post(
        "/demo/run",
        json={
            "text": "Escalation owner: NOC\nVendor contact: remy.lopez@supplyline.net\nSession secret: sk-session-SUPPLY7788",
            "task_type": "easy",
            "policy_mode": "external_sharing",
            "content_format": "email",
            "agent": "rules",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert any("remy.lopez@supplyline.net" in item for item in payload["risk_report"])
    assert any("sk-session-SUPPLY7788" in item for item in payload["risk_report"])


def test_demo_run_risk_report_is_safe_when_input_is_safe():
    response = client.post(
        "/demo/run",
        json={
            "text": "Operations update\nThe billing queue returned to normal latency after the deploy.",
            "task_type": "easy",
            "policy_mode": "training_safe",
            "content_format": "email",
            "agent": "rules",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_report"] == ["No obvious high-risk markers detected"]


def test_demo_compare_endpoint():
    response = client.post(
        "/demo/compare",
        json={
            "text": "Escalation owner: NOC\nVendor contact: remy.lopez@supplyline.net\nBridge line: 3125550109",
            "task_type": "easy",
            "policy_mode": "external_sharing",
            "content_format": "email",
            "agents": ["random", "rules"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload["runs"].keys()) == {"random", "rules"}


def test_demo_report_endpoint_returns_file_or_not_found():
    response = client.get("/demo/report")
    assert response.status_code in {200, 404}
