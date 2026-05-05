# Smart assistant — Backend

Django 5 + DRF + simplejwt (cookie auth) + django-mptt + drf-spectacular.

> Birinchi iteratsiya: auth, users, organisations, directions, info (lookup). Keyingi sprintlarda: events, reports, chat, notifications, web push, telegram bot, websocket (Channels), Celery.

## Talablar

- Python 3.12+ (3.14 sinab ko'rilgan)
- pip / venv

## O'rnatish

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
# yoki
source .venv/bin/activate # macOS/Linux

pip install -r requirements.txt
```

## Sozlash

```bash
cp .env.example .env
# .env'da SECRET_KEY ni o'zgartiring
```

## Migratsiyalar

```bash
python manage.py migrate
```

## Seed (test ma'lumotlar)

```bash
python manage.py seed
```

Yaratiladi:
- 8 ta rol (`SUPER_ADMIN`, `PREMIER_MINISTER`, `VICE_MINISTER`, `ASSISTANT_PREMIER`, `HEAD`, `ASSISTANT`, `ADMIN`, `EMPLOYEE`)
- 2 ta region (Toshkent shahri, Toshkent viloyati) + 11 ta tuman
- 1 ta tashkilot (Madaniyat vazirligi)
- 4 ta direction (Vazir + 3 ta bola)
- 6 ta test foydalanuvchi (parol: `Admin12345!`):
  - `superadmin` — SUPER_ADMIN (Django emergency admin uchun ham `is_superuser=True`)
  - `premier` — PREMIER_MINISTER
  - `vice1` — VICE_MINISTER
  - `admin1` — ADMIN
  - `head1` — HEAD
  - `employee1` — EMPLOYEE

## Ishga tushirish

```bash
python manage.py runserver 8081
```

- API base: http://localhost:8081/api/
- Swagger UI: http://localhost:8081/api/schema/swagger-ui/
- OpenAPI JSON: http://localhost:8081/api/schema/
- Django emergency admin: http://localhost:8081/admin/django/ (faqat `is_superuser`)

## API endpointlar (birinchi iteratsiya)

### Auth
- `POST /api/auth/login/` — body `{username, password}` → cookie set
- `POST /api/auth/logout/` — cookie clear
- `POST /api/auth/refresh/` — refresh cookie'dan yangi access generatsiya

### Users
- `GET /api/users/me/` — joriy foydalanuvchi
- `PUT /api/users/me/` — profilni tahrirlash (multipart `avatar` qo'llab-quvvatlanadi)
- `PATCH /api/users/me/password/` — parolni o'zgartirish
- `GET /api/users/?page=&page_size=&search=&role=&direction=&enabled=&status=`
- `GET /api/users/vice/` — vice ministrlar (faqat PREMIER, SUPER_ADMIN)
- `GET /api/users/chatters/`
- `GET /api/users/participants/?direction_id=&organisation_id=`
- **Admin** (SUPER_ADMIN, ADMIN):
  - `POST /api/users/`
  - `GET/PUT/PATCH/DELETE /api/users/{id}/`
  - `PATCH /api/users/{id}/status/` — body `{status}`
  - `POST /api/users/{id}/reset-password/` — body `{new_password?}` (optional)
  - `POST /api/users/{id}/clear-telegram/`

### Directions
- `GET /api/directions/?parent_id=&search=`
- `GET /api/directions/tree/`
- `GET /api/directions/{id}/`
- **Admin:** POST/PUT/DELETE

### Organisations
- `GET /api/organisations/?search=&page=&page_size=`
- `GET /api/organisations/tree/`
- `GET /api/organisations/{id}/`
- **Admin:** POST/PUT/DELETE

### Regions / Districts
- `GET/POST /api/regions/`, `GET/PUT/DELETE /api/regions/{id}/`
- `GET/POST /api/districts/?region_id=`, `GET/PUT/DELETE /api/districts/{id}/`

### Info (lookup)
- `GET /api/info/spheres/` — `[{value, label}]`
- `GET /api/info/types/`
- `GET /api/info/task-replies/` — `[{value, label, color}]`
- `GET /api/info/request-replies/`
- `GET /api/info/roles/` — `[{value, label}]`
- `GET /api/info/roles-full/` — `[{id, name, label_uz, label_ru}]`
- `GET /api/info/role-names/`
- `GET /api/info/statuses/`
- `GET /api/info/regions/`, `GET /api/info/districts/?region_id=`

## Frontend bilan integratsiya

- Frontend `withCredentials: true` ishlatadi
- CORS `localhost:5173` (Vite) uchun ochiq
- JWT cookie nomlari: `access_token`, `refresh_token`
- Cookie `HttpOnly`, prod'da `Secure` + `SameSite=Lax`

## Strukturasi

```
assistant_back/
├── manage.py
├── requirements.txt
├── .env.example
│
├── assistant/              # Django project
│   ├── settings/{base,dev,prod}.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
└── apps/
    ├── core/               # AuditMixin, JWT cookie auth, permissions, exception handler, seed command
    ├── users/              # User, Role, /me, admin CRUD, status, reset-password
    ├── organisations/      # Region, District, Organisation (MPTT)
    ├── directions/         # Direction (MPTT)
    ├── auth_app/           # /api/auth/{login,logout,refresh}/
    └── info/               # /api/info/* lookup endpoints
```

## Keyingi qadamlar

1. **Events/PreEvents** ilovasi — tadbirlar, qatnashchilar, fayllar, kalendar query
2. **Reports** — task / request, reply
3. **Chat** — REST + Channels WebSocket
4. **Notifications** — multi-channel + Web Push (pywebpush, VAPID)
5. **Attachments** — secure_upload (python-magic)
6. **Telegram bot** — aiogram FSM
7. **Celery** — background tasks, beat reminders
8. **Channels** — WebSocket (asgi.py to'liq tuzilishi)
9. **PostgreSQL** ga ko'chish (prod) — `dj-database-url`

## Test qilish (smoke)

```bash
# Login
curl -c cookies.txt -X POST http://localhost:8081/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"Admin12345!"}'

# /me/
curl -b cookies.txt http://localhost:8081/api/users/me/

# Vice list
curl -b cookies.txt http://localhost:8081/api/users/vice/
```
