"""Environment-backed configuration for the AutoBook application."""

import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(RuntimeError):
    """Raised when a required application setting is missing or invalid."""


def get_database_url() -> str:
    """Return the configured database URL or the local PostgreSQL default.

    Returns:
        The SQLAlchemy URL from ``DATABASE_URL``.
    """
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://autobook:autobook@127.0.0.1:5432/autobook",
    )


def get_jwt_secret() -> str:
    """Return the JWT signing secret without a success-shaped fallback.

    Returns:
        The non-empty secret configured in ``JWT_SECRET``.

    Raises:
        ConfigurationError: If ``JWT_SECRET`` is unset or blank.
    """
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise ConfigurationError("JWT_SECRET is not configured.")
    return secret


def get_timezone() -> ZoneInfo:
    """Return the configured service timezone.

    Returns:
        The IANA timezone from ``APP_TIMEZONE``; defaults to ``Europe/Kyiv``.

    Raises:
        ZoneInfoNotFoundError: If the configured timezone is not available.
    """
    return ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Kyiv"))
