# Docker Setup for CashmoneyDjango

This document provides instructions for running the CashmoneyDjango application using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Configuration

1. Create a `.env` file based on the `.env.example` template:

```bash
cp .env.example .env
```

2. Edit the `.env` file and set the appropriate values:

```
# Security
SECRET_KEY=your-secure-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=cashmoney
DB_USER=cashmoneyuser
DB_PASSWORD=your-secure-password
DB_HOST=db
DB_PORT=5432
```

Note: When using Docker, `DB_HOST` should be set to `db` (the service name in compose.yaml).

## Running the Application

### Start all services

```bash
docker compose up -d
```

This will start:
- PostgreSQL database on port 5432
- Django application on port 8000
- Streamlit frontend on port 8501

### View logs

```bash
docker compose logs -f
```

### Stop all services

```bash
docker compose down
```

### Rebuild containers after changes

```bash
docker compose up -d --build
```

## Accessing the Application

- Django Admin: http://localhost:8000/admin/
- Streamlit Frontend: http://localhost:8501/

## Development Mode

For development, you can mount your local directory to see changes in real-time:

```bash
docker compose up -d
```

The compose.yaml already includes volume mounts for development.

## Database Management

### Creating a superuser

```bash
docker compose exec django python manage.py createsuperuser
```

### Running migrations

```bash
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate
```

### Backing up the database

```bash
docker compose exec db pg_dump -U cashmoneyuser cashmoney > backup.sql
```

## Troubleshooting

### Common Issues


### Checking container status

```bash
docker compose ps
```

### Accessing container shell

```bash
docker compose exec django /bin/bash
docker compose exec streamlit /bin/bash
docker compose exec db /bin/bash
```

### Viewing container logs

```bash
docker compose logs -f django
docker compose logs -f streamlit
docker compose logs -f db
```
