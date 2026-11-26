"""FastAPI application entry point."""

from fastapi import FastAPI

from src.api.router import router
from src.core.errors import register_error_handlers
from src.core.logging import RequestLoggingMiddleware, configure_logging

configure_logging()

app = FastAPI(title="AutoBook SDD API", version="1.0.0")
register_error_handlers(app)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(router)
