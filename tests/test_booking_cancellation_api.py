"""API contract tests for client booking cancellation."""

from datetime import timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import Response

from tests.conftest import (
    CANCELLATION_NOW,
    TEST_JWT_SECRET,
)

API_PATH = "/api/v1/bookings/{booking_id}/cancel"


def _token(
    user_id: UUID,
    role: str = "CLIENT",
    expiration: int = 4_102_444_800,
) -> str:
    """Create a token with deterministic claims for one API scenario.

    Args:
        user_id: UUID placed in the token subject.
        role: Documented role claim.
        expiration: JWT expiration timestamp, fixed for deterministic cases.

    Returns:
        An HS256 bearer token.
    """
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": expiration},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


def _headers(
    user_id: UUID,
    role: str = "CLIENT",
    expiration: int = 4_102_444_800,
) -> dict[str, str]:
    """Return a bearer header for a documented API identity.

    Args:
        user_id: UUID placed in the token subject.
        role: Documented role claim.
        expiration: JWT expiration timestamp, fixed for deterministic cases.

    Returns:
        Authorization header containing an HS256 bearer token.
    """
    return {"Authorization": f"Bearer {_token(user_id, role, expiration)}"}


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


def _cancel(
    client: TestClient,
    booking_id: UUID | str,
    user_id: UUID,
    body: dict[str, str] | None = None,
    role: str = "CLIENT",
    expiration: int = 4_102_444_800,
) -> Response:
    """Send a cancellation request with deterministic client credentials.

    Args:
        client: FastAPI test client.
        booking_id: Existing booking UUID or path value.
        user_id: JWT subject UUID.
        body: Optional cancellation request body.
        role: JWT role claim.
        expiration: JWT expiration timestamp.

    Returns:
        The API response.
    """
    return client.patch(
        API_PATH.format(booking_id=booking_id),
        headers=_headers(user_id, role, expiration),
        json=body,
    )


def test_cancel_confirmed_booking_succeeds(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Expect successful cancellation per docs/user_guide.md, section 3.5."""
    booking = booking_factory()
    response = _cancel(
        api_client,
        booking.booking_id,
        booking.owner_id,
        {"reason": "Переніс візит"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(booking.booking_id)
    assert body["status"] == "CANCELLED_BY_CLIENT"
    assert body["cancel_reason"] == "Переніс візит"


def test_reason_is_omitted_when_not_supplied(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Omit absent cancel_reason per docs/decisions.md, decision 19."""
    booking = booking_factory()
    response = _cancel(api_client, booking.booking_id, booking.owner_id)

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED_BY_CLIENT"
    assert "cancel_reason" not in response.json()


@pytest.mark.parametrize("reason", ["", "   "])
def test_empty_or_whitespace_reason_is_omitted(
    api_client: TestClient,
    booking_factory,
    reason: str,
) -> None:
    """Treat empty and whitespace-only reasons as absent per docs/decisions.md, decision 20."""
    booking = booking_factory()
    response = _cancel(
        api_client,
        booking.booking_id,
        booking.owner_id,
        {"reason": reason},
    )

    assert response.status_code == 200
    assert "cancel_reason" not in response.json()


def test_reason_with_255_unicode_characters_is_accepted(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Accept 255 Unicode characters per docs/decisions.md, decision 20."""
    booking = booking_factory()
    reason = "я" * 255
    response = _cancel(
        api_client,
        booking.booking_id,
        booking.owner_id,
        {"reason": reason},
    )

    assert response.status_code == 200
    assert response.json()["cancel_reason"] == reason


def test_reason_with_256_characters_is_validation_error(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Reject 256 characters per docs/api/openapi.yaml, cancel 400 response."""
    booking = booking_factory()
    response = _cancel(
        api_client,
        booking.booking_id,
        booking.owner_id,
        {"reason": "я" * 256},
    )

    assert response.status_code == 400
    _assert_problem(response, 400, "https://autobook.local/errors/validation-error")


@pytest.mark.parametrize(
    "status",
    [
        "PENDING",
        "REJECTED",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED_BY_CLIENT",
        "CANCELLED_BY_ADMIN",
        "NO_SHOW",
    ],
)
def test_non_confirmed_booking_is_rejected(
    api_client: TestClient,
    booking_factory,
    status: str,
) -> None:
    """Reject every non-CONFIRMED state per docs/decisions.md, decision 16."""
    booking = booking_factory(status=status)
    response = _cancel(api_client, booking.booking_id, booking.owner_id)

    assert response.status_code == 400
    _assert_problem(
        response,
        400,
        "https://autobook.local/errors/cancellation-not-allowed",
    )


def test_repeated_cancellation_is_rejected(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Reject the second transition per docs/decisions.md, decision 16."""
    booking = booking_factory()
    first_response = _cancel(api_client, booking.booking_id, booking.owner_id)
    second_response = _cancel(api_client, booking.booking_id, booking.owner_id)

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    _assert_problem(
        second_response,
        400,
        "https://autobook.local/errors/cancellation-not-allowed",
    )


def test_cancellation_exactly_two_hours_before_start_succeeds(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Allow the inclusive two-hour boundary per docs/decisions.md, decision 6."""
    booking = booking_factory(starts_in=timedelta(hours=2))
    assert booking.start_time == CANCELLATION_NOW + timedelta(hours=2)

    response = _cancel(api_client, booking.booking_id, booking.owner_id)

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED_BY_CLIENT"


def test_cancellation_less_than_two_hours_before_start_is_rejected(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Reject less than two hours per docs/decisions.md, decision 6."""
    booking = booking_factory(starts_in=timedelta(hours=1, minutes=59))
    assert booking.start_time == CANCELLATION_NOW + timedelta(hours=1, minutes=59)

    response = _cancel(api_client, booking.booking_id, booking.owner_id)

    assert response.status_code == 400
    _assert_problem(response, 400, "https://autobook.local/errors/late-cancellation")


def test_foreign_and_missing_bookings_share_not_found_problem(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Hide foreign booking ownership per docs/decisions.md, decision 4."""
    booking = booking_factory()
    foreign_response = _cancel(
        api_client,
        booking.booking_id,
        booking.other_client_id,
    )
    missing_response = _cancel(api_client, uuid4(), booking.owner_id)

    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
    _assert_problem(foreign_response, 404, "https://autobook.local/errors/not-found")
    _assert_problem(missing_response, 404, "https://autobook.local/errors/not-found")
    foreign_problem = foreign_response.json()
    missing_problem = missing_response.json()
    for field in ("type", "title", "status", "detail"):
        assert foreign_problem[field] == missing_problem[field]


def test_malformed_booking_uuid_is_not_found(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Treat invalid id as unavailable per docs/api/openapi.yaml and GAP-LOG.md, GAP-006."""
    booking = booking_factory()
    response = _cancel(api_client, "not-a-uuid", booking.owner_id)

    assert response.status_code == 404
    _assert_problem(response, 404, "https://autobook.local/errors/not-found")


@pytest.mark.parametrize("role", ["MASTER", "ADMIN"])
def test_non_client_role_is_forbidden(
    api_client: TestClient,
    booking_factory,
    role: str,
) -> None:
    """Reject other roles per docs/decisions.md, decision 10, and GAP-LOG.md, GAP-005."""
    booking = booking_factory()
    response = _cancel(
        api_client,
        booking.booking_id,
        booking.owner_id,
        role=role,
    )

    assert response.status_code == 403
    _assert_problem(response, 403, "https://autobook.local/errors/forbidden")


def test_cancellation_without_token_is_unauthorized(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Require a bearer token per docs/user_guide.md, section 2."""
    booking = booking_factory()
    response = api_client.patch(
        API_PATH.format(booking_id=booking.booking_id),
    )

    assert response.status_code == 401
    _assert_problem(response, 401, "https://autobook.local/errors/unauthorized")


def test_expired_token_is_unauthorized(
    api_client: TestClient,
    booking_factory,
) -> None:
    """Reject expired JWTs per docs/user_guide.md, sections 2 and 4."""
    booking = booking_factory()
    response = _cancel(
        api_client,
        booking.booking_id,
        booking.owner_id,
        expiration=1,
    )

    assert response.status_code == 401
    _assert_problem(response, 401, "https://autobook.local/errors/unauthorized")


def test_missing_jwt_secret_is_configuration_error(
    api_client: TestClient,
    booking_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report absent JWT_SECRET per docs/user_guide.md, section 4."""
    booking = booking_factory()
    headers = _headers(booking.owner_id)
    monkeypatch.delenv("JWT_SECRET")

    response = api_client.patch(
        API_PATH.format(booking_id=booking.booking_id),
        headers=headers,
    )

    assert response.status_code == 500
    _assert_problem(
        response,
        500,
        "https://autobook.local/errors/configuration-error",
    )
