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

## License

This project is proprietary software.
