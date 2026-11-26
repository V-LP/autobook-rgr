"""Bearer JWT verification dependency for protected API operations."""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from src.core.config import ConfigurationError, get_jwt_secret
from src.core.errors import ApiProblem

bearer_scheme = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """Roles recognized from verified JWT claims."""

    CLIENT = "CLIENT"
    MASTER = "MASTER"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity and role extracted from a verified bearer JWT."""

    user_id: UUID
    role: UserRole


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Verify bearer credentials and return their subject UUID and role.

    Args:
        credentials: HTTP bearer credentials supplied with the request.

    Returns:
        The authenticated user identity.

    Raises:
        ApiProblem: If credentials are missing or invalid, or JWT configuration
            is missing.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiProblem(
            status=401,
            type_uri="https://autobook.local/errors/unauthorized",
            title="Unauthorized",
            detail="Потрібна авторизація.",
        )

    try:
        secret = get_jwt_secret()
    except ConfigurationError as exc:
        raise ApiProblem(
            status=500,
            type_uri="https://autobook.local/errors/configuration-error",
            title="Configuration Error",
            detail="На сервері не налаштовано JWT_SECRET.",
        ) from exc

    try:
        claims = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "role", "exp"]},
        )
        user_id = UUID(claims["sub"])
        role = UserRole(claims["role"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise ApiProblem(
            status=401,
            type_uri="https://autobook.local/errors/unauthorized",
            title="Unauthorized",
            detail="Токен відсутній, недійсний або прострочений.",
        ) from None

    return AuthenticatedUser(user_id=user_id, role=role)
