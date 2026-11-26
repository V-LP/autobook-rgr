"""Create a repeatable local client, vehicle, service, shift, and booking."""

from datetime import datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from src.core.clock import get_clock
from src.core.config import get_timezone
from src.core.database import get_session_factory
from src.models import (
    AuditLog,
    Booking,
    BookingService,
    Master,
    ScheduleShift,
    Service,
    User,
    Vehicle,
)

CLIENT_ID = UUID("30000000-0000-4000-8000-000000000001")
VEHICLE_ID = UUID("40000000-0000-4000-8000-000000000001")
SERVICE_ID = UUID("10000000-0000-4000-8000-000000000030")
MASTER_ID = UUID("20000000-0000-4000-8000-000000000001")
SHIFT_ID = UUID("60000000-0000-4000-8000-000000000001")
BOOKING_ID = UUID("50000000-0000-4000-8000-000000000001")
AUDIT_ID = UUID("70000000-0000-4000-8000-000000000001")


def main() -> None:
    """Seed deterministic demo data without deleting other database rows."""
    timezone = get_timezone()
    start_date = get_clock().date() + timedelta(days=1)
    start_time = datetime.combine(start_date, time(10, 0), tzinfo=timezone)
    end_time = start_time + timedelta(minutes=30)
    session_factory = get_session_factory()

    with session_factory.begin() as session:
        session.merge(
            User(
                id=CLIENT_ID,
                email="demo-client@example.invalid",
                password_hash="unusable-demo-password-hash",
                full_name="Demo Client",
                role="CLIENT",
                status="ACTIVE",
            )
        )
        session.flush()
        session.merge(
            Vehicle(
                id=VEHICLE_ID,
                user_id=CLIENT_ID,
                make="Demo",
                model="Vehicle",
                year=2020,
                license_plate="DEMO123",
            )
        )
        session.merge(
            Service(
                id=SERVICE_ID,
                title="Demo service 30 min",
                duration_min=30,
                price=Decimal("300.00"),
                is_active=True,
            )
        )
        session.merge(Master(id=MASTER_ID, full_name="Demo Master"))
        session.flush()
        session.merge(
            ScheduleShift(
                id=SHIFT_ID,
                master_id=MASTER_ID,
                shift_date=start_date,
                start_time=time(9, 0),
                end_time=time(18, 0),
                break_start=time(13, 0),
                break_end=time(14, 0),
            )
        )
        session.merge(
            Booking(
                id=BOOKING_ID,
                booking_number="BK-DEMO-0001",
                client_id=CLIENT_ID,
                vehicle_id=VEHICLE_ID,
                master_id=MASTER_ID,
                status="PENDING",
                start_time=start_time,
                end_time=end_time,
            )
        )
        session.merge(
            BookingService(
                booking_id=BOOKING_ID,
                service_id=SERVICE_ID,
                price_at_booking=Decimal("300.00"),
            )
        )
        session.merge(
            AuditLog(
                id=AUDIT_ID,
                actor_id=CLIENT_ID,
                action="BOOKING_CREATED",
                entity_type="BOOKING",
                entity_id=BOOKING_ID,
                new_val='{"status":"PENDING"}',
            )
        )

    print(f"Client ID: {CLIENT_ID}")
    print(f"Vehicle ID: {VEHICLE_ID}")
    print(f"Service ID: {SERVICE_ID}")
    print(f"Master ID: {MASTER_ID}")
    print(f"Slot: {start_time.isoformat()} - {end_time.isoformat()}")
    print(f"Booking ID: {BOOKING_ID}")


if __name__ == "__main__":
    main()
