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

### Installation

1. Clone the repository
2. Create a `.env` file with your database credentials
3. Run `docker-compose up` to start the services

### Environment Variables

Configure these variables in your `.env` file:

- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `DB_HOST` - Database host
- `DB_PORT` - Database port

## API Documentation

Access the Swagger API documentation at `/swagger/` when the server is running.

## Development

The project uses Django REST Framework for building APIs and includes custom middleware for error handling and authentication.

## License

This project is proprietary software.
