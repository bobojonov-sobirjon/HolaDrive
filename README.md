# HoloDrive

A ride-sharing platform backend similar to Uber, built with Django REST Framework.

## About

HoloDrive is a mobile backend API that connects passengers with drivers. The platform enables users to request rides, track locations, and manage their accounts through a secure REST API.

## Features

- User authentication and authorization with JWT tokens
- Custom user profiles with location tracking
- RESTful API endpoints
- Swagger API documentation
- Docker containerization
- PostgreSQL database
- CORS support for mobile applications

## Technology Stack

- Django 5.2.8
- Django REST Framework
- PostgreSQL
- Docker & Docker Compose
- JWT Authentication
- Swagger/OpenAPI Documentation

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Environment Variables

Create a `.env` file in the project root with:

```env
DB_NAME=holo-drive
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=db
DB_PORT=5432
```

---

## Docker

### Build and Run

```bash
# Build and start containers (foreground)
docker compose up --build

# Or run in background (detached)
docker compose up -d --build
```

- **API:** http://127.0.0.1:8000
- **Swagger docs:** http://127.0.0.1:8000/swagger/

### Migrations

Migrations run automatically on container start (via `entrypoint.sh`).

**Manual migration** (containers running):

```bash
docker compose exec web python manage.py migrate
```

**Migration when containers are stopped:**

```bash
docker compose run --rm web python manage.py migrate
```

### Other Useful Commands

```bash
# Create superuser
docker compose exec web python manage.py createsuperuser

# Django shell
docker compose exec web python manage.py shell

# View logs
docker compose logs -f web

# Stop containers
docker compose down

# Stop and remove volumes (resets database)
docker compose down -v
```

## API Documentation

Access the Swagger API documentation at `/swagger/` when the server is running.

## Development

The project uses Django REST Framework for building APIs and includes custom middleware for error handling and authentication.

## Daphne va Celery (ishga tushirish)

**Daphne** — Django **ASGI** serveri (WebSocket / Channels uchun). **Celery** — fon vazifalar (masalan, order timeout tekshirish). Broker sifatida **Redis** ishlatiladi (`CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` — `config/settings.py`).

### Talablar

- Virtual muhit faollashtirilgan bo‘lsin, bog‘liqliklar o‘rnatilgan bo‘lsin: `pip install -r requirements.txt`
- **Redis** ishlayotgan bo‘lsi (masalan `redis://localhost:6379/0`). Windows uchun [Redis](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/) yoki WSL/Docker orqali.

`.env` da (ixtiyoriy, default localhost):

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Daphne (lokal)

Loyiha ildizidan:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Yoki qisqa shakl:

```bash
daphne config.asgi:application --bind 0.0.0.0 --port 8000
```

**Docker** da `web` servisi allaqachon shu buyruq bilan ishga tushadi (`docker-compose.yml`).

### Celery Worker (lokal)

Yangi terminal — vazifalarni bajaruvchi worker:

```bash
celery -A config worker --loglevel=info
```

**Windows:** `config/celery.py` ichida `worker_pool = 'solo'` avtomatik qo‘llanadi (prefork Windows’da muammoli).

### Celery Beat (lokal, vaqtli vazifalar)

Yana bitta terminal — masalan har 5 soniyada `check_order_timeouts`:

```bash
celery -A config beat --loglevel=info
```

> Ishlab chiqishda odatda **3 ta jarayon** kerak: **Daphne** (API + WebSocket), **Celery worker**, **Celery beat** (+ **Redis**).

### Qisqa tekshiruv

```bash
celery -A config inspect active
```

## License

This project is proprietary software.
