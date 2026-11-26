"""Pydantic schemas used by the AutoBook HTTP API."""

from pydantic import BaseModel, ConfigDict, Field


class CancelBookingRequest(BaseModel):
    """Optional reason supplied with a booking cancellation request."""

    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(default=None, max_length=255)


class BookingResponse(BaseModel):
    """Booking state returned by booking operations."""

    id: str
    status: str
    booking_number: str | None = None
    start_time: str | None = None
    cancel_reason: str | None = None


class ErrorResponse(BaseModel):
    """RFC 7807 problem response used for all HTTP errors."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
