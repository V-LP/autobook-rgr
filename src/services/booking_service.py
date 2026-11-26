"""Business rules for cancelling client bookings."""

from datetime import datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from src.models.entities import Booking
from src.repositories.audit_repository import add_status_change
from src.repositories.booking_repository import find_booking_for_update

logger = structlog.get_logger("autobook").bind(component="booking")


class BookingNotFoundError(Exception):
    """Raised when a booking is missing or does not belong to the client."""


class CancellationNotAllowedError(Exception):
    """Raised when the booking is not in the confirmed state."""


class LateCancellationError(Exception):
    """Raised when cancellation is requested less than two hours before start."""


def cancel_booking(
    session: Session,
    booking_id: str,
    client_id: UUID,
    reason: str | None,
    now: datetime,
) -> Booking:
    """Cancel a confirmed booking within the documented time window.

    Args:
        session: SQLAlchemy session used for the atomic booking and audit update.
        booking_id: String UUID identifying the requested booking.
        client_id: UUID of the authenticated client.
        reason: Optional cancellation reason, at most 255 characters.
        now: Timezone-aware current time supplied by the application clock.

    Returns:
        The updated booking with its optional cancellation reason.

    Raises:
        BookingNotFoundError: If the UUID is invalid or the booking is not owned.
        CancellationNotAllowedError: If the current booking status is not confirmed.
        LateCancellationError: If fewer than two hours remain before the booking.
    """
    try:
        parsed_booking_id = UUID(booking_id)
    except ValueError:
        raise BookingNotFoundError from None

    with session.begin():
        booking = find_booking_for_update(session, parsed_booking_id, client_id)
        if booking is None:
            raise BookingNotFoundError
        if booking.status != "CONFIRMED":
            raise CancellationNotAllowedError
        if booking.start_time - now < timedelta(hours=2):
            raise LateCancellationError

        normalized_reason = reason if reason and reason.strip() else None
        previous_status = booking.status
        booking.status = "CANCELLED_BY_CLIENT"
        booking.cancel_reason = normalized_reason
        add_status_change(
            session,
            actor_id=client_id,
            entity_id=booking.id,
            old_status=previous_status,
            new_status=booking.status,
        )
        session.flush()

    logger.info(
        "booking_cancelled",
        reason_present=normalized_reason is not None,
        reason_length=len(normalized_reason) if normalized_reason is not None else 0,
    )
    return booking
