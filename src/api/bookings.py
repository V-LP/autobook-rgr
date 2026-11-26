"""HTTP endpoints for booking operations."""

from fastapi import APIRouter, Depends, status

from src.api.schemas import CancelBookingRequest, ErrorResponse
from src.core.auth import AuthenticatedUser, UserRole, get_current_user
from src.core.errors import ApiProblem

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.patch(
    "/{id}/cancel",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    responses={
        403: {
            "description": "Операцію дозволено лише клієнту.",
            "content": {
                "application/problem+json": {
                    "schema": ErrorResponse.model_json_schema(),
                }
            },
        },
        501: {
            "description": "Скасування ще не реалізовано.",
            "content": {
                "application/problem+json": {
                    "schema": ErrorResponse.model_json_schema(),
                }
            },
        }
    },
)
async def cancel_booking(
    id: str,
    payload: CancelBookingRequest | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Expose the cancellation route as an authenticated, not-yet-implemented stub.

    Args:
        id: Booking UUID from the path.
        payload: Optional cancellation reason accepted by the API schema.
        current_user: Identity supplied by the verified bearer-token dependency.

    Raises:
        ApiProblem: If the caller is not a client or cancellation is not implemented.
    """
    del id, payload
    if current_user.role is not UserRole.CLIENT:
        raise ApiProblem(
            status=403,
            type_uri="https://autobook.local/errors/forbidden",
            title="Forbidden",
            detail="Недостатньо прав.",
        )
    raise ApiProblem(
        status=501,
        type_uri="https://autobook.local/errors/not-implemented",
        title="Not Implemented",
        detail="Операція скасування бронювання ще не реалізована.",
    )
