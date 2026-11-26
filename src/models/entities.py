"""SQLAlchemy entities for the documented AutoBook database schema."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class User(Base):
    """Client or staff identity referenced by bookings and audit records."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class Vehicle(Base):
    """Vehicle owned by a user and referenced by a booking."""

    __tablename__ = "vehicles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    license_plate: Mapped[str] = mapped_column(String(32), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Master(Base):
    """Service master that can own schedule shifts and bookings."""

    __tablename__ = "masters"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)


class Service(Base):
    """Catalog service with a duration and price snapshot source."""

    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint(
            "duration_min >= 30 AND duration_min % 30 = 0",
            name="ck_services_duration_min",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False)


class ScheduleShift(Base):
    """Master shift and optional break boundaries."""

    __tablename__ = "schedule_shifts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    master_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("masters.id"), nullable=False
    )
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_end: Mapped[time | None] = mapped_column(Time, nullable=True)


class Booking(Base):
    """Booking state, interval, and optional cancellation reason."""

    __tablename__ = "bookings"
    __table_args__ = (
        Index(
            "idx_no_double_booking",
            "master_id",
            "start_time",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'CONFIRMED', 'IN_PROGRESS')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    booking_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    client_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    vehicle_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    master_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("masters.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class BookingService(Base):
    """Association between a booking and a service with its price snapshot."""

    __tablename__ = "booking_services"

    booking_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id"), primary_key=True
    )
    service_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("services.id"), primary_key=True
    )
    price_at_booking: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)


class AuditLog(Base):
    """PII-free status audit record for a persisted entity."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    old_val: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_val: Mapped[str | None] = mapped_column(Text, nullable=True)
