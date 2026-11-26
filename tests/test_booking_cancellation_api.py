"""API contract tests for client booking cancellation."""

from collections.abc import Iterator
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import Response

from src.core.clock import get_clock
from src.main import app

API_PATH = "/api/v1/bookings/{booking_id}/cancel"
JWT_SECRET = "test-only-signing-key-32-bytes-long"
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
CLIENT_ID = "30000000-0000-4000-8000-000000000001"
OTHER_CLIENT_ID = "30000000-0000-4000-8000-000000000002"
BOOKING_ID = "50000000-0000-4000-8000-000000000001"


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Provide an API client with a deterministic clock and JWT secret.

    Yields:
        TestClient with the cancellation clock dependency overridden.
    """
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_clock] = lambda: NOW
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = previous_overrides


def _token(user_id: str = CLIENT_ID, role: str = "CLIENT") -> str:
    """Create a deterministic, non-expired bearer token for an API request.

    Args:
        user_id: UUID placed in the token subject.
        role: Documented role claim.

    Returns:
        An HS256 JWT with a fixed expiration in the future.
    """
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": 4_102_444_800},
        JWT_SECRET,
        algorithm="HS256",
    )


def _headers(user_id: str = CLIENT_ID, role: str = "CLIENT") -> dict[str, str]:
    """Return the bearer header for the requested documented identity.

    Args:
        user_id: UUID placed in the token subject.
        role: Documented role claim.

    Returns:
        Authorization header containing an HS256 bearer token.
    """
    return {"Authorization": f"Bearer {_token(user_id, role)}"}


def _assert_problem(response: Response, status: int, type_uri: str) -> None:
    """Assert the documented RFC 7807 media type and required response fields.

    Args:
        response: API response to validate.
        status: Expected HTTP status and problem status.
        type_uri: Expected problem type URI.
    """
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert {"type", "title", "status", "detail", "instance"} <= problem.keys()
    assert problem["type"] == type_uri
    assert problem["status"] == status


def test_cancel_confirmed_booking_succeeds(api_client: TestClient) -> None:
    """Expect a successful cancellation per docs/user_guide.md, section 3.5."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
        json={"reason": "Переніс візит"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CANCELLED_BY_CLIENT"
    assert body["cancel_reason"] == "Переніс візит"


def test_non_confirmed_booking_is_rejected(api_client: TestClient) -> None:
    """Expect cancellation-not-allowed per docs/decisions.md, decision 16."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
    )

    assert response.status_code == 400
    _assert_problem(
        response,
        400,
        "https://autobook.local/errors/cancellation-not-allowed",
    )


def test_cancellation_less_than_two_hours_before_start_is_rejected(
    api_client: TestClient,
) -> None:
    """Expect late-cancellation per docs/decisions.md, decision 6."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
    )

    assert response.status_code == 400
    _assert_problem(
        response,
        400,
        "https://autobook.local/errors/late-cancellation",
    )


def test_cancellation_exactly_two_hours_before_start_succeeds(
    api_client: TestClient,
) -> None:
    """Expect the inclusive two-hour boundary per docs/decisions.md, decision 6."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED_BY_CLIENT"


def test_reason_with_255_characters_is_accepted(api_client: TestClient) -> None:
    """Expect the maximum reason length per docs/decisions.md, decision 20."""
    reason = "я" * 255
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
        json={"reason": reason},
    )

    assert response.status_code == 200
    assert response.json()["cancel_reason"] == reason


def test_reason_with_256_characters_is_validation_error(api_client: TestClient) -> None:
    """Expect validation-error per docs/api/openapi.yaml, cancel 400 response."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
        json={"reason": "я" * 256},
    )

    assert response.status_code == 400
    _assert_problem(response, 400, "https://autobook.local/errors/validation-error")


@pytest.mark.parametrize("reason", ["", "   "])
def test_empty_reason_is_omitted_from_response(
    api_client: TestClient,
    reason: str,
) -> None:
    """Treat empty and whitespace-only reasons as absent per docs/decisions.md, decision 20."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
        json={"reason": reason},
    )

    assert response.status_code == 200
    assert "cancel_reason" not in response.json()


def test_missing_reason_is_omitted_from_response(api_client: TestClient) -> None:
    """Omit absent cancel_reason per docs/decisions.md, decision 19."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(),
    )

    assert response.status_code == 200
    assert "cancel_reason" not in response.json()


def test_missing_and_foreign_bookings_share_not_found_problem(
    api_client: TestClient,
) -> None:
    """Hide booking ownership per docs/decisions.md, decision 4."""
    path = API_PATH.format(booking_id=BOOKING_ID)
    missing_response = api_client.patch(path, headers=_headers())
    foreign_response = api_client.patch(
        path,
        headers=_headers(user_id=OTHER_CLIENT_ID),
    )

    assert missing_response.status_code == 404
    assert foreign_response.status_code == 404
    _assert_problem(missing_response, 404, "https://autobook.local/errors/not-found")
    _assert_problem(foreign_response, 404, "https://autobook.local/errors/not-found")
    assert missing_response.json() == foreign_response.json()


def test_cancellation_without_token_is_unauthorized(api_client: TestClient) -> None:
    """Require bearer authentication per docs/user_guide.md, section 2."""
    response = api_client.patch(API_PATH.format(booking_id=BOOKING_ID))

    assert response.status_code == 401
    _assert_problem(response, 401, "https://autobook.local/errors/unauthorized")


def test_cancellation_with_non_client_role_is_forbidden(api_client: TestClient) -> None:
    """Reject other roles per GAP-LOG.md, GAP-005."""
    response = api_client.patch(
        API_PATH.format(booking_id=BOOKING_ID),
        headers=_headers(role="MASTER"),
    )

    assert response.status_code == 403
    _assert_problem(response, 403, "https://autobook.local/errors/forbidden")
