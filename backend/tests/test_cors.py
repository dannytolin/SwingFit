from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_cors_preflight():
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_cors_header_on_get():
    response = client.get(
        "/",
        headers={"Origin": "http://localhost:5173"},
    )
    # With allow_credentials=True the middleware reflects the specific origin
    # rather than the wildcard "*" (required by the CORS spec).
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin in ("*", "http://localhost:5173")
