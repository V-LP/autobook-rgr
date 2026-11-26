"""Application clock dependency using the service timezone."""

from datetime import datetime

from src.core.config import get_timezone


def get_clock() -> datetime:
    """Return the current timezone-aware time in the configured service timezone.

    Returns:
        Current wall-clock time in ``Europe/Kyiv`` by default.
    """
    return datetime.now(get_timezone())
