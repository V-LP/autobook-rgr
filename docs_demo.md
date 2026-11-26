# Cancellation API demo (PowerShell)

Run these commands from the repository root. The API is served on port 8001.
The demo JWT secret is for local use only.

## Prepare demo data

Start PostgreSQL and create the demo data. The seed includes a `PENDING`
booking; the SQL below prepares it for cancellation and creates a second
confirmed booking less than two hours away.

```powershell
docker compose up -d db
$env:DATABASE_URL = "postgresql+psycopg://autobook:autobook@127.0.0.1:5432/autobook"
$env:JWT_SECRET = "local-only-change-this-demo-secret"
alembic upgrade head
python scripts\demo_seed.py

$bookingId = "50000000-0000-4000-8000-000000000001"
$lateBookingId = "50000000-0000-4000-8000-000000000002"
$prepareSql = "UPDATE bookings SET status = 'CONFIRMED', cancel_reason = NULL WHERE id = '$bookingId';"
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U autobook -d autobook -c $prepareSql

$lateSql = "INSERT INTO bookings (id, booking_number, client_id, vehicle_id, master_id, status, start_time, end_time) VALUES ('$lateBookingId', 'BK-DEMO-LATE-0002', '30000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001', 'CONFIRMED', now() + interval '119 minutes', now() + interval '149 minutes') ON CONFLICT (id) DO UPDATE SET status = 'CONFIRMED', start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time;"
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U autobook -d autobook -c $lateSql
```

In another PowerShell window, start the API:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://autobook:autobook@127.0.0.1:5432/autobook"
$env:JWT_SECRET = "local-only-change-this-demo-secret"
uvicorn src.main:app --port 8001
```

Create CLIENT tokens and UTF-8 request bodies in the first PowerShell window.
Using UTF-8 files avoids PowerShell's native-argument encoding when passing
JSON to `curl.exe`.

```powershell
$base = "http://127.0.0.1:8001"
$clientId = "30000000-0000-4000-8000-000000000001"
$otherClientId = "30000000-0000-4000-8000-000000000002"
$env:JWT_SECRET = "local-only-change-this-demo-secret"
$clientToken = python scripts\make_token.py $clientId
$otherToken = python scripts\make_token.py $otherClientId

New-Item -ItemType Directory -Force reports | Out-Null
$reasonFile = Join-Path $PWD "reports\cancel-reason.json"
$longReasonFile = Join-Path $PWD "reports\cancel-reason-256.json"
[System.IO.File]::WriteAllText($reasonFile, '{"reason":"Rescheduled"}', [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($longReasonFile, '{"reason":"' + ("x" * 256) + '"}', [System.Text.UTF8Encoding]::new($false))
```

## Requests and captured responses

### Successful cancellation

```powershell
curl.exe -i -X PATCH "$base/api/v1/bookings/$bookingId/cancel" `
  -H "Authorization: Bearer $clientToken" `
  -H "Content-Type: application/json" `
  --data-binary "@$reasonFile"
```

```text
HTTP/1.1 200 OK
Content-Type: application/json

{"id":"50000000-0000-4000-8000-000000000001","status":"CANCELLED_BY_CLIENT","booking_number":"BK-DEMO-0001","start_time":"2026-11-28T08:00:00Z","cancel_reason":"Rescheduled"}
```

### Repeat cancellation

```powershell
curl.exe -i -X PATCH "$base/api/v1/bookings/$bookingId/cancel" `
  -H "Authorization: Bearer $clientToken"
```

```text
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json

{"type":"https://autobook.local/errors/cancellation-not-allowed","title":"Cancellation Not Allowed","status":400,"detail":"Скасування можливе лише для підтвердженого бронювання.","instance":"/api/v1/bookings/50000000-0000-4000-8000-000000000001/cancel"}
```

### Another client's booking

```powershell
curl.exe -i -X PATCH "$base/api/v1/bookings/$bookingId/cancel" `
  -H "Authorization: Bearer $otherToken"
```

```text
HTTP/1.1 404 Not Found
Content-Type: application/problem+json

{"type":"https://autobook.local/errors/not-found","title":"Booking Not Found","status":404,"detail":"Бронювання не знайдено.","instance":"/api/v1/bookings/50000000-0000-4000-8000-000000000001/cancel"}
```

### Less than two hours before the appointment

```powershell
curl.exe -i -X PATCH "$base/api/v1/bookings/$lateBookingId/cancel" `
  -H "Authorization: Bearer $clientToken"
```

```text
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json

{"type":"https://autobook.local/errors/late-cancellation","title":"Late Cancellation Denied","status":400,"detail":"Скасування можливе не пізніше ніж за 2 години до початку візиту.","instance":"/api/v1/bookings/50000000-0000-4000-8000-000000000002/cancel"}
```

### Missing token

```powershell
curl.exe -i -X PATCH "$base/api/v1/bookings/$bookingId/cancel"
```

```text
HTTP/1.1 401 Unauthorized
Content-Type: application/problem+json

{"type":"https://autobook.local/errors/unauthorized","title":"Unauthorized","status":401,"detail":"Потрібна авторизація.","instance":"/api/v1/bookings/50000000-0000-4000-8000-000000000001/cancel"}
```

### Reason with 256 characters

```powershell
curl.exe -i -X PATCH "$base/api/v1/bookings/$bookingId/cancel" `
  -H "Authorization: Bearer $clientToken" `
  -H "Content-Type: application/json" `
  --data-binary "@$longReasonFile"
```

```text
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json

{"type":"https://autobook.local/errors/validation-error","title":"Validation Error","status":400,"detail":"Параметри запиту або тіло мають помилку формату.","instance":"/api/v1/bookings/50000000-0000-4000-8000-000000000001/cancel"}
```

Remove the temporary request bodies when finished:

```powershell
Remove-Item -LiteralPath $reasonFile, $longReasonFile
```

## Contract check

The six responses have the statuses declared for `cancelBooking`; their
success body and problem responses match the declared schemas. The 256-character
reason response uses the documented status and schema, but its `detail` differs
from the specific `reason_too_long` example. Schemathesis ran against only
`cancelBooking`; its output is in `reports/schemathesis.txt`. It found a
coverage failure for an undeclared TRACE request returning 405 without an
`Allow` header. Both observations are recorded in `GAP-LOG.md`.
