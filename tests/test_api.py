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
