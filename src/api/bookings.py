"""HTTP endpoints for booking operations."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.schemas import BookingResponse, CancelBookingRequest, ErrorResponse
from src.core.auth import AuthenticatedUser, UserRole, get_current_user
from src.core.clock import get_clock
from src.core.database import get_db_session
from src.core.errors import ApiProblem
from src.services.booking_service import (
    BookingNotFoundError,
    CancellationNotAllowedError,
    LateCancellationError,
)
from src.services.booking_service import (
    cancel_booking as cancel_booking_service,
)

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.patch(
    "/{id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=BookingResponse,
    response_model_exclude_none=True,
    responses={
        401: {
            "description": "Потрібна автентифікація.",
            "content": {
                "application/problem+json": {
                    "schema": ErrorResponse.model_json_schema(),
                }
            },
        },
        403: {
            "description": "Операцію дозволено лише клієнту.",
            "content": {
                "application/problem+json": {
                    "schema": ErrorResponse.model_json_schema(),
                }
            },
        },
        400: {
            "description": "Скасування заборонене або запізніле.",
            "content": {
                "application/problem+json": {
                    "schema": ErrorResponse.model_json_schema(),
                }
            },
        },
        404: {
            "description": "Бронювання не знайдено.",
            "content": {
                "application/problem+json": {
                    "schema": ErrorResponse.model_json_schema(),
                }
            },
        },
    },
)
async def cancel_booking(
    id: str,
    payload: CancelBookingRequest | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
    now: datetime = Depends(get_clock),
) -> BookingResponse:
    """Cancel a confirmed booking owned by the authenticated client.

    Args:
        id: Booking UUID from the path.
        payload: Optional cancellation reason accepted by the API schema.
        current_user: Identity supplied by the verified bearer-token dependency.
        session: Request-scoped SQLAlchemy session.
        now: Time supplied by the injectable service clock.

    Returns:
        The cancelled booking state, omitting absent optional values.

    Raises:
        ApiProblem: If the caller is not a client or cancellation is not allowed.
    """
    if current_user.role is not UserRole.CLIENT:
        raise ApiProblem(
            status=403,
            type_uri="https://autobook.local/errors/forbidden",
            title="Forbidden",
            detail="Недостатньо прав.",
        )
    try:
        booking = cancel_booking_service(
            session=session,
            booking_id=id,
            client_id=current_user.user_id,
            reason=payload.reason if payload is not None else None,
            now=now,
        )
    except BookingNotFoundError:
        raise ApiProblem(
            status=404,
            type_uri="https://autobook.local/errors/not-found",
            title="Booking Not Found",
            detail="Бронювання не знайдено.",
        ) from None
    except CancellationNotAllowedError:
        raise ApiProblem(
            status=400,
            type_uri="https://autobook.local/errors/cancellation-not-allowed",
            title="Cancellation Not Allowed",
            detail="Скасування можливе лише для підтвердженого бронювання.",
        ) from None
    except LateCancellationError:
        raise ApiProblem(
            status=400,
            type_uri="https://autobook.local/errors/late-cancellation",
            title="Late Cancellation Denied",
            detail="Скасування можливе не пізніше ніж за 2 години до початку візиту.",
        ) from None

    return BookingResponse(
        id=str(booking.id),
        status=booking.status,
        booking_number=booking.booking_number,
        start_time=booking.start_time,
        cancel_reason=booking.cancel_reason,
    )
