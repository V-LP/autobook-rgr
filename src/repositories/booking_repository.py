"""Persistence operations used by booking cancellation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.entities import Booking


def find_booking_for_update(
    session: Session,
    booking_id: UUID,
    client_id: UUID,
) -> Booking | None:
    """Find and lock a booking only when it belongs to the requesting client.

    Args:
        session: Active SQLAlchemy transaction session.
        booking_id: UUID of the requested booking.
        client_id: UUID of the authenticated client.

    Returns:
        The locked booking, or ``None`` for a missing or foreign booking.
    """
    statement = (
        select(Booking)
        .where(Booking.id == booking_id, Booking.client_id == client_id)
        .with_for_update()
    )
    return session.scalar(statement)
