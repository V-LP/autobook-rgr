"""Persistence operations for PII-free audit events."""

from uuid import UUID

from sqlalchemy.orm import Session

from src.models.entities import AuditLog


def add_status_change(
    session: Session,
    actor_id: UUID,
    entity_id: UUID,
    old_status: str,
    new_status: str,
) -> None:
    """Stage a status-only audit event in the caller's transaction.

    Args:
        session: Active SQLAlchemy transaction session.
        actor_id: UUID of the client making the status change.
        entity_id: UUID of the changed booking.
        old_status: Previous booking status.
        new_status: Resulting booking status.
    """
    session.add(
        AuditLog(
            actor_id=actor_id,
            action="BOOKING_STATUS_CHANGED",
            entity_type="Booking",
            entity_id=entity_id,
            old_val=f'{{"status":"{old_status}"}}',
            new_val=f'{{"status":"{new_status}"}}',
        )
    )
