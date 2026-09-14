from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_dependencies(monkeypatch):
    monkeypatch.setattr("app.main.check_mysql", lambda: True)
    monkeypatch.setattr("app.main.check_chroma", lambda: True)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "mysql": "ok",
        "chroma": "ok",
    }
