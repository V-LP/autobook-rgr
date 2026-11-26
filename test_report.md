# Cancellation API test report

Command: `python -m pytest`

Result: **9 failed, 8 passed** (17 tests collected).

## Expected RED failures

The nine failing checks all receive HTTP `501 Not Implemented` from the
cancellation route where the documented contract expects:

- `200`: confirmed-booking success, exactly two hours before start, 255-character
  reason, empty reason (both empty and whitespace-only), and omitted reason.
- `400`: non-`CONFIRMED` booking and cancellation less than two hours before
  start.
- `404`: missing/foreign booking with the same problem response.

These are assertion failures against the current unimplemented route, not test
setup, import, fixture, or clock errors. The test clock is fixed through the
`get_clock()` dependency override.

## Passing tests

Eight tests passed: the 256-character reason validation, missing-token and
non-client-role authorization checks, and all five existing skeleton tests.
