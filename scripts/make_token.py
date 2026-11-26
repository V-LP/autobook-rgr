"""Create a short-lived local JWT for a demo user."""

import argparse
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from src.core.auth import UserRole
from src.core.config import ConfigurationError, get_jwt_secret


def main() -> None:
    """Validate CLI arguments and print a one-day HS256 bearer token."""
    parser = argparse.ArgumentParser(description="Create a local AutoBook JWT.")
    parser.add_argument("user_id", type=UUID, help="UUID to place in the JWT sub claim")
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=UserRole.CLIENT.value,
        help="Role claim (default: CLIENT)",
    )
    arguments = parser.parse_args()

    try:
        secret = get_jwt_secret()
    except ConfigurationError as exc:
        parser.error(str(exc))

    expires_at = datetime.now(UTC) + timedelta(days=1)
    token = jwt.encode(
        {
            "sub": str(arguments.user_id),
            "role": arguments.role,
            "exp": expires_at,
        },
        secret,
        algorithm="HS256",
    )
    print(token)


if __name__ == "__main__":
    main()
