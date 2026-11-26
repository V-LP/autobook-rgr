"""Tests for the API skeleton and core dependencies."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from src.core.clock import get_clock
from src.main import app


def test_cancel_stub_requires_bearer_authentication() -> None:
    """Requests without a bearer token receive the standard 401 problem."""
    response = TestClient(app).patch("/api/v1/bookings/00000000-0000-4000-8000-000000000001/cancel")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "https://autobook.local/errors/unauthorized"


def test_cancel_stub_rejects_non_client_role(monkeypatch) -> None:
    """A valid staff token is rejected before the cancellation stub executes."""
    secret = "test-only-signing-key-32-bytes-long"
    monkeypatch.setenv("JWT_SECRET", secret)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "MASTER",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    response = TestClient(app).patch(
        "/api/v1/bookings/00000000-0000-4000-8000-000000000001/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "https://autobook.local/errors/forbidden"


def test_clock_returns_service_timezone() -> None:
    """The default application clock is timezone-aware in Europe/Kyiv."""
    now = get_clock()

    assert now.tzinfo is not None
    assert now.tzinfo.key == "Europe/Kyiv"
