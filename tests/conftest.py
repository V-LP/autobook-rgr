"""Shared isolated database and clock fixtures for API tests."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.core.clock import get_clock
from src.core.database import Base, get_db_session
from src.main import app
from src.models.entities import Booking, Master, User, Vehicle

CANCELLATION_NOW = datetime(2026, 11, 10, 9, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
TEST_JWT_SECRET = "test-only-signing-key-32-bytes-long"


@event.listens_for(Booking, "load")
def restore_sqlite_timezone(booking: Booking, context: object) -> None:
    """Restore the documented service timezone lost by SQLite datetime storage.

    Args:
        booking: ORM booking loaded from the test database.
        context: SQLAlchemy load context.
    """
    for field in ("start_time", "end_time"):
        value = getattr(booking, field)
        if value.tzinfo is None:
            setattr(booking, field, value.replace(tzinfo=ZoneInfo("Europe/Kyiv")))


@dataclass(frozen=True)
class CancellationBooking:
    """IDs and start time for one isolated cancellation API scenario."""

    booking_id: UUID
    owner_id: UUID
    other_client_id: UUID
    start_time: datetime


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    """Create an isolated in-memory database using the project ORM schema.

    Yields:
        SQLite engine with the documented AutoBook tables created.
    """
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Provide one session for the fixture records and API request.

    Args:
        db_engine: Isolated engine for this test.

    Yields:
        SQLAlchemy session bound to the isolated database.
    """
    with Session(db_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def api_client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Provide an API client with isolated database and fixed application time.

    Args:
        db_session: Isolated session used by the API request.
        monkeypatch: Pytest environment and dependency-override manager.

    Yields:
        TestClient with database and clock dependencies overridden.
    """
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    previous_overrides = app.dependency_overrides.copy()

    def override_db_session() -> Iterator[Session]:
        """Yield this test's session instead of opening the configured database."""
        yield db_session

    def override_clock() -> datetime:
        """Return the deterministic timestamp used by cancellation scenarios."""
        return CANCELLATION_NOW

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_clock] = override_clock
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides = previous_overrides


@pytest.fixture
def booking_factory(
    db_session: Session,
) -> Callable[..., CancellationBooking]:
    """Create independent clients, vehicles, masters, and bookings for a test.

    Args:
        db_session: Isolated session used to persist valid fixture rows.

    Returns:
        Factory accepting a booking status and start offset from the fixed clock.
    """

    def create_booking(
        status: str = "CONFIRMED",
        starts_in: timedelta = timedelta(hours=3),
    ) -> CancellationBooking:
        """Persist a valid booking fixture with a client-owned vehicle.

        Args:
            status: Initial state of the booking under test.
            starts_in: Offset from the fixed application clock to visit start.

        Returns:
            IDs and start time for the newly created scenario.
        """
        owner_id = uuid4()
        other_client_id = uuid4()
        vehicle_id = uuid4()
        master_id = uuid4()
        booking_id = uuid4()
        start_time = CANCELLATION_NOW + starts_in

        db_session.add_all(
            [
                User(
                    id=owner_id,
                    email=f"{owner_id}@example.test",
                    password_hash="test-hash",
                    full_name="Test Client",
                    role="CLIENT",
                    status="ACTIVE",
                ),
                User(
                    id=other_client_id,
                    email=f"{other_client_id}@example.test",
                    password_hash="test-hash",
                    full_name="Other Client",
                    role="CLIENT",
                    status="ACTIVE",
                ),
                Vehicle(
                    id=vehicle_id,
                    user_id=owner_id,
                    make="Test",
                    model="Vehicle",
                    year=2020,
                    license_plate=f"T-{vehicle_id.hex[:10]}",
                ),
                Master(
                    id=master_id,
                    full_name="Test Master",
                ),
                Booking(
                    id=booking_id,
                    booking_number=f"BK-{booking_id.hex}",
                    client_id=owner_id,
                    vehicle_id=vehicle_id,
                    master_id=master_id,
                    status=status,
                    start_time=start_time,
                    end_time=start_time + timedelta(minutes=30),
                ),
            ]
        )
        db_session.commit()
        return CancellationBooking(
            booking_id=booking_id,
            owner_id=owner_id,
            other_client_id=other_client_id,
            start_time=start_time,
        )

    return create_booking
