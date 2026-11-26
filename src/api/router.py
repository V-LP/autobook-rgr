"""Top-level API router assembly."""

from fastapi import APIRouter

from src.api.bookings import router as bookings_router

router = APIRouter(prefix="/api/v1")
router.include_router(bookings_router)
