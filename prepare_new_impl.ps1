# Готує сім бронювань у БД НОВОЇ реалізації (autobook-rgr). Запускати з кореня autobook-rgr
# після docker compose up -d db, alembic upgrade head, python scripts\demo_seed.py.
# Повторний запуск повертає бронювання в початковий стан.
$client = "30000000-0000-4000-8000-000000000001"
$vehicle = "40000000-0000-4000-8000-000000000001"
$master = "20000000-0000-4000-8000-000000000001"
$rows = @(
  @("60000000-0000-4000-8000-000000000001","BK-CMP-0001","CONFIRMED","now() + interval '3 days'"),
  @("60000000-0000-4000-8000-000000000002","BK-CMP-0002","CONFIRMED","now() + interval '3 days'"),
  @("60000000-0000-4000-8000-000000000003","BK-CMP-0003","CONFIRMED","now() + interval '3 days'"),
  @("60000000-0000-4000-8000-000000000004","BK-CMP-0004","CONFIRMED","now() + interval '3 days'"),
  @("60000000-0000-4000-8000-000000000005","BK-CMP-0005","CONFIRMED","now() + interval '3 days'"),
  @("60000000-0000-4000-8000-000000000006","BK-CMP-0006","PENDING","now() + interval '3 days'"),
  @("60000000-0000-4000-8000-000000000007","BK-CMP-0007","CONFIRMED","now() + interval '90 minutes'")
)
foreach ($r in $rows) {
  $sql = "INSERT INTO bookings (id, booking_number, client_id, vehicle_id, master_id, status, start_time, end_time, cancel_reason) VALUES ('$($r[0])','$($r[1])','$client','$vehicle','$master','$($r[2])',$($r[3]),$($r[3]) + interval '30 minutes',NULL) ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, start_time=EXCLUDED.start_time, end_time=EXCLUDED.end_time, cancel_reason=NULL;"
  docker compose exec -T db psql -v ON_ERROR_STOP=1 -U autobook -d autobook -c $sql
}
# Бронювання confirmed_foreign належить тому ж клієнту; "чужим" воно є для токена other_client_id.
