"""RFC 7807 error types and FastAPI exception handlers."""

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.schemas import ErrorResponse
from src.core.config import ConfigurationError

logger = structlog.get_logger("autobook").bind(component="errors")


class ApiProblem(Exception):
    """An expected API error with an RFC 7807 status and type.

    Args:
        status: HTTP status code.
        type_uri: Stable URI identifying the problem category.
        title: Short human-readable problem title.
        detail: Safe detail text for the API consumer.
    """

    def __init__(self, status: int, type_uri: str, title: str, detail: str) -> None:
        """Store the public problem details without internal exception data."""
        super().__init__(detail)
        self.status = status
        self.type_uri = type_uri
        self.title = title
        self.detail = detail


def _problem_response(
    request: Request,
    status: int,
    type_uri: str,
    title: str,
    detail: str,
) -> JSONResponse:
    """Build the standard RFC 7807 JSON response.

    Args:
        request: Request used to populate the problem instance.
        status: HTTP status code.
        type_uri: Stable URI identifying the problem category.
        title: Short problem title.
        detail: Safe detail text for the API consumer.

    Returns:
        A JSON response with media type ``application/problem+json``.
    """
    body = ErrorResponse(
        type=type_uri,
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=status,
        content=body.model_dump(),
        media_type="application/problem+json",
    )


async def handle_api_problem(request: Request, exc: ApiProblem) -> JSONResponse:
    """Convert an expected API problem into the shared response shape.

    Args:
        request: Incoming request.
        exc: Expected problem raised by an API dependency or operation.

    Returns:
        An RFC 7807 JSON response.
    """
    return _problem_response(
        request,
        exc.status,
        exc.type_uri,
        exc.title,
        exc.detail,
    )


async def handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Convert framework HTTP errors into RFC 7807 responses.

    Args:
        request: Incoming request.
        exc: HTTP exception raised by FastAPI or Starlette.

    Returns:
        An RFC 7807 JSON response without internal details.
    """
    common_problems = {
        401: (
            "https://autobook.local/errors/unauthorized",
            "Unauthorized",
            "Потрібна авторизація.",
        ),
        403: (
            "https://autobook.local/errors/forbidden",
            "Forbidden",
            "Недостатньо прав.",
        ),
        404: (
            "https://autobook.local/errors/not-found",
            "Not Found",
            "Ресурс не знайдено.",
        ),
    }
    type_uri, title, detail = common_problems.get(
        exc.status_code,
        (
            "https://autobook.local/errors/http-error",
            "HTTP Error",
            "Запит не може бути виконаний.",
        ),
    )
    return _problem_response(request, exc.status_code, type_uri, title, detail)


async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Map request validation failures to the documented HTTP 400 format.

    Args:
        request: Incoming request.
        exc: FastAPI validation error; values are not copied into the response.

    Returns:
        A generic validation problem response.
    """
    return _problem_response(
        request,
        400,
        "https://autobook.local/errors/validation-error",
        "Validation Error",
        "Параметри запиту або тіло мають помилку формату.",
    )


async def handle_configuration_error(
    request: Request,
    exc: ConfigurationError,
) -> JSONResponse:
    """Map missing server configuration to a safe HTTP 500 response.

    Args:
        request: Incoming request.
        exc: Configuration failure; its message is not exposed.

    Returns:
        A configuration problem response.
    """
    return _problem_response(
        request,
        500,
        "https://autobook.local/errors/configuration-error",
        "Configuration Error",
        "На сервері не налаштовано необхідну конфігурацію.",
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic problem response for unexpected server errors.

    Args:
        request: Incoming request.
        exc: Unexpected exception; details are not logged or returned.

    Returns:
        A generic internal-server problem response.
    """
    logger.error("unhandled_exception", exception_type=type(exc).__name__)
    return _problem_response(
        request,
        500,
        "https://autobook.local/errors/internal-server-error",
        "Internal Server Error",
        "Сталася внутрішня помилка сервера.",
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform handlers for API, validation, and server errors.

    Args:
        app: FastAPI application receiving the handlers.
    """
    app.add_exception_handler(ApiProblem, handle_api_problem)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(ConfigurationError, handle_configuration_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
