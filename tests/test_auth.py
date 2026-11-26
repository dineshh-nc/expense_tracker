import pytest

BODY = {"email": "new@example.com", "password": "testpass123"}

PROTECTED = [
    "/auth/me",
    "/categories",
    "/transactions",
    "/reports/monthly?month=2026-11",
    "/reports/daily?month=2026-11",
    "/reports/compare?month=2026-11",
]


def test_register_and_duplicate_email(anonymous_client):
    first = anonymous_client.post("/auth/register", json=BODY)

    assert first.status_code == 201
    assert first.json()["email"] == "new@example.com"
    assert "password" not in first.json()
    assert "password_hash" not in first.json()
    assert anonymous_client.post("/auth/register", json=BODY).status_code == 409


def test_login_with_wrong_password(anonymous_client):
    anonymous_client.post("/auth/register", json=BODY)

    response = anonymous_client.post(
        "/auth/login", data={"username": BODY["email"], "password": "wrongpass1"}
    )

    assert response.status_code == 401


def test_me_returns_current_user(client):
    assert client.get("/auth/me").json()["email"] == "user@example.com"


@pytest.mark.parametrize("path", PROTECTED)
def test_endpoints_require_login(anonymous_client, path):
    assert anonymous_client.get(path).status_code == 401


def test_invalid_token_is_rejected(anonymous_client):
    response = anonymous_client.get(
        "/transactions", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


def test_short_password_is_rejected(anonymous_client):
    response = anonymous_client.post(
        "/auth/register", json={"email": "a@example.com", "password": "short"}
    )

    assert response.status_code == 422