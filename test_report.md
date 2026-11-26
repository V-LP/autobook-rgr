# Cancellation API test report

Commands:

- `ruff check src tests` — passed.
- `ruff format --check src tests` — passed (25 files already formatted).
- `python -m pytest -q` — **26 passed, 0 failed**.

No test failures remain. Coverage includes successful cancellation, reason
handling and length boundaries, foreign/missing/malformed booking IDs, each
non-`CONFIRMED` state, repeated cancellation, both time boundaries, role and
token authorization, expired JWTs, missing `JWT_SECRET`, and RFC 7807 fields.

The test database is isolated per case. Because SQLite drops timezone metadata
from `DateTime(timezone=True)`, its test-only ORM load listener restores the
documented `Europe/Kyiv` timezone; API time is supplied through the fixed
`get_clock()` override.
