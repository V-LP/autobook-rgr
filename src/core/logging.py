"""Structured JSON logging and request logging middleware."""

import logging
import sys
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp


def configure_logging() -> None:
    """Configure structured JSON logging to standard output."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
        force=True,
    )
    logging.getLogger("uvicorn.access").disabled = True
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request lifecycle metadata without headers or request bodies."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize request logging middleware.

        Args:
            app: The ASGI application wrapped by the middleware.
        """
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request start and completion without sensitive request data.

        Args:
            request: The incoming HTTP request.
            call_next: The next ASGI request handler.

        Returns:
            The HTTP response produced by the application.
        """
        request_id = str(uuid4())
        logger = structlog.get_logger("autobook").bind(
            component="http",
            request_id=request_id,
        )
        started = perf_counter()
        logger.info("request_started", method=request.method)
        response = await call_next(request)
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            method=request.method,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
        )
        return response
