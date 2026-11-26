"""Create the initial AutoBook schema."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all documented entities and the booking conflict index."""
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
    )
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("make", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("license_plate", sa.String(length=32), nullable=False),
        sa.Column("vin", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "duration_min >= 30 AND duration_min % 30 = 0",
            name="ck_services_duration_min",
        ),
    )
    op.create_table(
        "masters",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
    )
    op.create_table(
        "schedule_shifts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "master_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("masters.id"),
            nullable=False,
        ),
        sa.Column("shift_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("booking_number", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "client_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("vehicles.id"),
            nullable=False,
        ),
        sa.Column(
            "master_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("masters.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancel_reason", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "booking_services",
        sa.Column(
            "booking_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("bookings.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "service_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("services.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("price_at_booking", sa.Numeric(), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "actor_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("old_val", sa.Text(), nullable=True),
        sa.Column("new_val", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_no_double_booking",
        "bookings",
        ["master_id", "start_time"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'CONFIRMED', 'IN_PROGRESS')"),
    )


def downgrade() -> None:
    """Drop the AutoBook schema in reverse dependency order."""
    op.drop_index("idx_no_double_booking", table_name="bookings")
    op.drop_table("audit_logs")
    op.drop_table("booking_services")
    op.drop_table("bookings")
    op.drop_table("schedule_shifts")
    op.drop_table("masters")
    op.drop_table("services")
    op.drop_table("vehicles")
    op.drop_table("users")
