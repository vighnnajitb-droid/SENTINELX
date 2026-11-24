
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "overall" in response.json()
    assert "checks" in response.json()


def test_login_invalid():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "wronguser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Incorrect username or password"
    }
