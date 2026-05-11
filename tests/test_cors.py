from fastapi.testclient import TestClient

from app.main import app


def test_login_preflight_allows_frontend_origin():
    with TestClient(app) as client:
        response = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:4000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4000"


def test_loopback_origin_receives_cors_header_on_regular_response():
    with TestClient(app) as client:
        response = client.get("/", headers={"Origin": "http://127.0.0.1:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
