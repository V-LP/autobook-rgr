# План реалізації скасування бронювання

## Межі та базові припущення

План створює потрібні компоненти з нуля: це не припускає наявності готових
роутерів, репозиторіїв, сервісів, авторизації, годинника, аудиту, обробників
помилок, моделей чи міграцій. Реалізується лише `PATCH
/api/v1/bookings/{id}/cancel` і мінімальні залежності для нього; API створення,
підтвердження, перегляду бронювань, видачі токенів та анонімізації не
додаються.

Джерела для вимог і правил — тільки наявні `docs/` та
[analysis.md](analysis.md). Рішення `GAP-001`–`GAP-010` зберігаються без змін;
нові рішення позначені `GAP-011` і `GAP-012` у [GAP-LOG.md](GAP-LOG.md).

## 1. Структура проєкту і технології

Архітектурний напрям залежностей: `api → services → repositories → models`;
`core` надає інфраструктурні залежності шарам. Це прямо відповідає
[docs/architecture.md, «Компоненти»](docs/architecture.md) і
[docs/coding_convention.md, «Структура проєкту»](docs/coding_convention.md).

| Тека / файл | Вміст і призначення |
|---|---|
| `pyproject.toml` | Python 3.12, метадані пакета, залежності FastAPI, SQLAlchemy 2, Alembic, PostgreSQL-драйвера та pytest; налаштування Ruff за конвенцією. |
| `compose.yaml` | Сервіс PostgreSQL 16 для локальної розробки й інтеграційних тестів; змінні доступу передавати через середовище, не фіксувати секрети. |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/` | Налаштування й версійна міграція схеми; upgrade/downgrade керуються Alembic. |
| `src/main.py` | Створити FastAPI app, підключити router, RFC 7807 error handlers і request logging middleware. |
| `src/api/router.py` | Реєстрація booking router під `/api/v1`. |
| `src/api/bookings.py` | Тонкий PATCH handler: прийняти схему, перевірену особу, DB session і clock; викликати сервіс; відобразити відповідь/доменні помилки. |
| `src/api/schemas.py` | Pydantic-схеми запиту скасування, відповіді бронювання та RFC 7807 problem response. |
| `src/services/booking_service.py` | Перевірки причини, власника, статусу, часового вікна; атомарне скасування. |
| `src/services/audit_service.py` | Побудувати статусну audit-подію без PII та передати її репозиторію в межах тієї самої транзакції. |
| `src/repositories/booking_repository.py` | Пошук із фільтром власника, блокування рядка, зміна статусу та причини. |
| `src/repositories/audit_repository.py` | Додати рядок `AuditLog` у передану сесію; не створювати окремої транзакції. |
| `src/models/entities.py` | SQLAlchemy 2 моделі сутностей, FK, унікальності й документовані обмеження. |
| `src/models/__init__.py` | Експорт моделей для Alembic metadata. |
| `src/core/config.py` | Зчитування `DATABASE_URL`, `JWT_SECRET` і зони СТО `Europe/Kyiv`; без вбудованих секретів. |
| `src/core/database.py` | SQLAlchemy engine/session factory, request-scoped session і межі транзакцій. |
| `src/core/auth.py` | Bearer JWT dependency: перевірити HS256, `sub`, `role`, `exp`; надати UUID користувача й роль. Видача токенів поза обсягом. |
| `src/core/clock.py` | Інжектована timezone-aware функція поточного часу для `Europe/Kyiv`, придатна до перевизначення в тестах. |
| `src/core/errors.py` | Єдині RFC 7807 responses, доменні помилки та їх перетворення на HTTP-коди/типи. |
| `src/core/logging.py` | Структуровані JSON-логи, request ID і маскування; причина скасування не логуються як текст. |
| `tests/conftest.py` | Фікстури SQLAlchemy session, тестового клієнта, фіксованого clock і підписаних тестових JWT. |
| `tests/unit/` | Ізольовані тести сервісних правил, часу, валідації, помилок і схем. |
| `tests/integration/` | PostgreSQL 16, Alembic, реальні FK/constraints, транзакційність маршруту й аудит. |
| `tests/contract/` | Перевірки маршруту, схем і HTTP-відповідей проти наявного OpenAPI. |

Python 3.12 та структура шарів визначені
[docs/coding_convention.md](docs/coding_convention.md); FastAPI, SQLAlchemy та
PostgreSQL — [docs/architecture.md](docs/architecture.md); Alembic і Docker
workflow — [docs/user_guide.md, «Підготовка локального середовища»](docs/user_guide.md);
pytest — команди в [docs/coding_convention.md, «Інструменти й команди»](docs/coding_convention.md).
Документація називає PostgreSQL без номера версії; PostgreSQL 16 і Docker
Compose для нього приймаються з уточнення цього завдання (GAP-012).

## 2. Простежуваність «документація → компонент коду»

| Частина документації | Компонент, який її реалізує |
|---|---|
| [docs/api/openapi.yaml, `PATCH /api/v1/bookings/{id}/cancel`, `BookingResponse`, `ErrorResponse`](docs/api/openapi.yaml) | `src/api/bookings.py`, `src/api/schemas.py`, `src/core/errors.py`; contract tests |
| [docs/user_guide.md, §§ 2, 3.5, 4](docs/user_guide.md) | `src/core/auth.py`, `src/api/bookings.py`, `src/services/booking_service.py`; auth і HTTP integration tests |
| [docs/architecture.md, «Компоненти»](docs/architecture.md) | `src/api/`, `src/services/`, `src/repositories/`, `src/models/`, `src/core/` із залежностями тільки згори вниз |
| [docs/architecture.md, «Скасування бронювання»](docs/architecture.md) | `BookingService.cancel_booking`, `BookingRepository`, transaction і clock injection |
| [docs/architecture.md, «Дані та ключі»](docs/architecture.md) | `src/models/entities.py`, початкова Alembic migration, FK/integrity integration tests |
| [docs/architecture.md, «Логування» й «Безпека»](docs/architecture.md) | `src/core/logging.py`, `src/core/auth.py`, перевірки відсутності PII в логах |
| [docs/architecture.md, «Анонімізація»](docs/architecture.md); [docs/user_guide.md, § 3.6](docs/user_guide.md) | Nullable `Booking.cancel_reason`; сумісність схеми та інтеграційний тест очищення поля без видалення історії |
| [docs/decisions.md, rows 6, 9–11, 14, 16–22](docs/decisions.md) | Clock/auth/audit/domain behavior у сервісах і core; unit та integration tests; із конфліктом PII — за GAP-002 |
| [docs/coding_convention.md, «Docstring», «Логування», «Обробка помилок»](docs/coding_convention.md) | Docstrings у публічних функціях/класах сервісів, core і репозиторіїв; structured logging та явні RFC 7807 errors |
| [docs/api/html/src.api.html](docs/api/html/src.api.html), [src.services.html](docs/api/html/src.services.html), [src.repositories.html](docs/api/html/src.repositories.html), [src.core.html](docs/api/html/src.core.html), [models.html](docs/api/html/models.html) | Розділення API/service/repository/core/model; при цьому задокументовані no-op аудиту реалізувати відповідно до GAP-008 |
| [docs/api/index.rst](docs/api/index.rst), [src.api.rst](docs/api/src.api.rst), [src.services.rst](docs/api/src.services.rst), [src.repositories.rst](docs/api/src.repositories.rst), [src.core.rst](docs/api/src.core.rst), [models.rst](docs/api/models.rst) | Імена Sphinx autodoc-модулів; після реалізації їхні публічні API мають мати docstrings за конвенцією |

## 3. Схема БД

### Обмеження, прямо взяті з документації

- UUID для ідентифікаторів; PK/FK та унікальності — як у таблиці
  [docs/architecture.md, «Дані та ключі»](docs/architecture.md).
- `bookings.booking_number` унікальний.
- `bookings.client_id`, `vehicle_id`, `master_id` посилаються відповідно на
  `users.id`, `vehicles.id`, `masters.id`.
- `cancel_reason` nullable, максимум 255 символів.
- `users.email` унікальний; nullable також `users.phone`, `vehicles.vin`,
  `masters.user_id`, межі перерв у `schedule_shifts`, `audit_logs.old_val` і
  `new_val`.
- Тривалість `services.duration_min` — не менше 30 хвилин і кратна 30.
- `booking_services` має складений PK із двох FK.
- `idx_no_double_booking` — унікальний частковий індекс на
  `(master_id, start_time)` для `PENDING`, `CONFIRMED`, `IN_PROGRESS`.
- Каскадне видалення кодом не задається.

### Таблиці й поля

Позначення `NOT NULL` нижче ставиться лише там, де це випливає з PK, контракту
чи заданої для плану вимоги про заповнюваність `Booking`. Інші неописані
nullability, точність `NUMERIC` та DB enum/check-деталі не видаються за вимоги
документації.

| Таблиця | Колонки й обмеження для початкової схеми |
|---|---|
| `users` | `id UUID PK`; `email` unique; `password_hash`; `full_name`; `phone NULL`; `role`; `status`. Роль ідентичності для скасування також надходить із JWT; видача/перевірка пароля поза обсягом. |
| `vehicles` | `id UUID PK`; `user_id UUID FK → users.id`; `make`; `model`; `year`; `license_plate`; `vin NULL`. Інтеграційний fixture має зв'язати `vehicles.user_id` із клієнтом бронювання. |
| `masters` | `id UUID PK`; `user_id UUID NULL FK → users.id`; `full_name`. Майстер потрібен як ціль `bookings.master_id`. |
| `services` | `id UUID PK`; `title`; `duration_min` з documented `>= 30` і кроком 30; `price`; `is_active`. Тип/точність ціни не задані. |
| `schedule_shifts` | `id UUID PK`; `master_id UUID FK → masters.id`; дата зміни; початок і кінець; nullable межі перерви. Потрібна для повної схеми пошуку слотів, але не для самого cancellation lookup. |
| `bookings` | `id UUID PK`; `booking_number` `NOT NULL UNIQUE`; `client_id UUID NOT NULL FK → users.id`; `vehicle_id UUID NOT NULL FK → vehicles.id`; `master_id UUID NOT NULL FK → masters.id`; `status NOT NULL`; `start_time` і `end_time` `NOT NULL`; `cancel_reason VARCHAR(255) NULL`. `start_time/end_time` — обране представлення документованого інтервалу; часові значення timezone-aware. |
| `booking_services` | `booking_id UUID FK → bookings.id`; `service_id UUID FK → services.id`; складений PK (`booking_id`, `service_id`); `price_at_booking`. |
| `audit_logs` | `id UUID PK`; `actor_id UUID FK → users.id`; `action`; тип сутності й ID сутності; `old_val TEXT NULL`; `new_val TEXT NULL`. Записувати лише ідентифікатори/тип дії та статуси, без reason чи іншого PII (GAP-002/003). |

### Як заповнити обов'язкові `Booking` FK/поля

Інтеграційні тести створюють чинні рядки в порядку залежностей, напряму через
test session, а не через API створення бронювання:

1. Створити `users` із UUID клієнта; JWT-фікстура використовує той самий UUID
   у `sub` та роль `CLIENT`.
2. Створити `vehicles` з унікальним UUID і `user_id` цього клієнта; заповнити
   поля авто, описані в архітектурі.
3. Створити `masters` з UUID і `full_name` (її `user_id` може бути `NULL`).
4. Створити `bookings` з UUID, `client_id`, `vehicle_id`, `master_id`,
   статусом `CONFIRMED`, timezone-aware `start_time`/`end_time` і унікальним
   тестовим `booking_number`.
5. Не створювати `services`, `booking_services` чи `schedule_shifts` лише для
   cancellation tests: скасування перевіряє власника, статус і час, а рішення
   про тестові бронювання допускає прямі вставки. Усі ці таблиці все одно
   створюються міграцією, бо належать задокументованій повній схемі.
6. Не виводити формат/генератор production `booking_number` із прикладу
   `BK-2026-001`. У межах цього модуля номер лише має бути присутнім і
   унікальним; fixture задає унікальне тестове значення. GAP-011 фіксує ці
   рішення.

Рішення про тип `end_time`, timezone-aware типи, nullability обов'язкових
booking columns і генерацію номерів у фікстурах обмежене вимогами цього
завдання; документація не задає повну фізичну схему (GAP-011).

## 4. Порядок реалізації малими етапами

| Етап | Зміст | Критерій завершення |
|---:|---|---|
| 1 | Створити `pyproject.toml`, каталог `src/`, тестові каталоги й `compose.yaml` з PostgreSQL 16. Визначити Python 3.12 та команди Ruff/pytest. | App/tests можна імпортувати; БД стартує локально без закомічених secrets. |
| 2 | Реалізувати `src/core/config.py`, `database.py` і `clock.py`; додати тестові overrides для DB session і часу. | Сесія має чітку request/transaction межу; clock повертає timezone-aware `Europe/Kyiv` value. |
| 3 | Створити `src/models/entities.py` для всіх таблиць з розділу 3; додати `alembic/env.py` та першу міграцію. | `alembic upgrade head` створює схему; downgrade повертає попередній стан; FK, nullable й індекси перевірені на PostgreSQL 16. |
| 4 | Реалізувати `src/core/auth.py`: Bearer JWT, HS256, claims `sub/role/exp`, відсутній secret як configuration error. | Unit tests для валідного/недійсного/простроченого токена; жоден secret/claim не логуються. |
| 5 | Реалізувати `src/core/errors.py` і `logging.py`; налаштувати FastAPI app з request-ID middleware. | Domain/validation errors виходять RFC 7807; логи мають структуровані поля, не містять PII. |
| 6 | Створити booking/audit repositories з пошуком за власником, блокуванням бронювання та staging змін у caller transaction. | Repository tests: однаковий результат для missing/foreign; запис status і audit використовує одну сесію. |
| 7 | Реалізувати `AuditService` і `BookingService.cancel_booking` з перевірками в порядку analysis; audit тільки status/IDs. | Unit tests для validation, ownership, state, time, reason normalization; failure у audit відкочує зміну бронювання. |
| 8 | Додати Pydantic request/response/problem schemas та booking router. Підключити auth, DB, clock і error mappings; не переносити бізнес-правила в route. | Contract tests підтверджують path/method, схеми, коди, медіатипи й response field omission. |
| 9 | Написати unit, integration і contract tests з розділу 5; створити fixtures з валідними users/vehicles/masters/bookings. | Цільовий набір проходить на PostgreSQL 16; boundary clock не використовує реальний час. |
| 10 | Прогнати `ruff check .`, `ruff format --check .`, `python -m pytest -q`; за наявності mypy прогнати необов'язковий `python -m mypy src`. Перевірити міграцію з порожньої БД. | Лінтер/форматер/тести успішні; схема відтворювана з нуля; усі public service/core/repository functions мають Google-style docstrings. |

Кожна додана публічна функція, клас і модуль у `src/services`, `src/core` та
`src/repositories` отримує Google-style docstring з застосовними `Args`,
`Returns`, `Raises`; рядки не довші за 100 символів.

## 5. План тестів: правило → перевірка

| Правило з [analysis.md, § г](analysis.md) | Тест(и) |
|---|---|
| `PATCH /api/v1/bookings/{id}/cancel`, Bearer JWT | Contract: маршрут приймає лише PATCH на точному шляху. Integration: без токена, некоректний і прострочений JWT дають `401 application/problem+json`; валідні `sub/role/exp` автентифікуються. |
| `reason` необов'язкова, межа 255 Unicode-символів; body validation перед lookup | Unit: відсутня причина й довжини 255 приймаються, Unicode довжини 256 відхиляється. Integration: 256 символів повертає 400 validation-error навіть із неіснуючим ID; repository lookup не викликається. |
| Порожня/whitespace-only причина відсутня | Unit + integration: `""` і рядок із пробілів дають відсутнє `cancel_reason` у БД та відповіді. Не-whitespace reason зберігається без trimming згідно з GAP-010. |
| Чуже й відсутнє бронювання мають однаковий `404` | Integration: запит із невідомим UUID і запит до іншого клієнта повертають однакові `status`, `type`, `title` і нейтральний `detail`; жодне не змінює БД. |
| Тільки `CLIENT` скасовує власне `CONFIRMED`; повторне/інше state дає `400 cancellation-not-allowed` | Integration: `MASTER`/`ADMIN` отримують вибране `403`; чужий запис не стає доступним. Unit: PENDING, REJECTED, IN_PROGRESS, COMPLETED і всі cancelled/no-show states відхиляються; другий PATCH після успішного першого дає cancellation-not-allowed. |
| Рівно за 2 години дозволено, менше — late-cancellation | Unit із зафіксованим clock: `start_time = now + 2h` успішний; `now + 1h59m` і `now + 1h59m59s` дають `400 late-cancellation`. Перевірити timezone-aware значення. |
| Успіх — `200`, `CANCELLED_BY_CLIENT`; reason повертається лише коли є | Contract: JSON response відповідає `BookingResponse`. Integration: успіх із reason має його значення, без reason поле ключа `cancel_reason` не має; не змінюються ID, власник та часовий інтервал. |
| Статус, reason у Booking і audit записуються атомарно; `AuditLog`/логи не містять PII | Integration: підтвердити один audit transition із ID та статусами і без reason; ін'єктована помилка запису аудиту відкочує статус/reason. Перехопити app logs і переконатися, що reason/JWT відсутні, а наявність/довжина reason допустимі. |
| Годинник лише через `get_clock()` у `Europe/Kyiv` | Unit: dependency override/fake clock керує межами незалежно від системного часу; smoke test перевіряє timezone-awareness. Не використовувати wall-clock у сервісі. |
| Anonymization очищає `Booking.cancel_reason` і зберігає історію | Schema/integration compatibility: `cancel_reason` приймає `NULL`, його відсутність не ламає response serialization, а наявні booking/audit rows не видаляються. Endpoint анонімізації не входить до scope цього модуля. |

Додаткові перевірки, що випливають із прогалин аналізу:

- Некоректний UUID у path повертає нейтральний `404` (GAP-006).
- Відсутній `JWT_SECRET` повертає `500 configuration-error` (GAP-007).
- RFC 7807 responses містять `type`, `title`, `status`, `detail`, `instance`;
  SQL, traceback і secret відсутні.
- Schema tests: дубль `booking_number` відхиляється; відсутні
  `vehicle_id`/`master_id`/`client_id`/start/end interval не проходять
  `NOT NULL`; дубль `users.email` відхиляється; nullable поля приймають `NULL`;
  FK на users/vehicles/masters/services відхиляють неіснуючих батьків;
  `booking_services` перевіряє складений PK; vehicle має бути прив'язаний до
  того самого client у fixture.
- Alembic integration: чистий upgrade створює всі документовані таблиці,
  UUID PK/FK, унікальний частковий індекс, який дозволяє однаковий
  `master_id/start_time` після переходу в неактивний status, і constraint
  тривалості послуг (30-хвилинні кратності від 30); downgrade не лишає
  часткової схеми.
- Concurrent cancellation: два одночасні запити до однієї confirmed booking
  дають не більше одного успіху й одного audit transition; другий запит
  після блокування бачить оновлений state (GAP-009).
