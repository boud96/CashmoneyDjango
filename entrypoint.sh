#!/bin/bash
set -e

wait_for_postgres() {
  echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
  # We use the variables passed from .env
  while ! nc -z $DB_HOST $DB_PORT; do
    sleep 0.1
  done
  echo "PostgreSQL is up and running!"
}

apply_migrations() {
  echo "Applying database migrations..."
  python manage.py migrate
}

# If the command is to run Django
if [ "$1" = "django" ]; then
  wait_for_postgres
  apply_migrations
  echo "Starting Django server on port ${DJANGO_PORT}..."
  python manage.py runserver 0.0.0.0:${DJANGO_PORT:-8000}


# If the command is to run Streamlit
elif [ "$1" = "streamlit" ]; then
  # REMOVED: wait_for_postgres (Streamlit doesn't talk to DB directly)

  echo "Starting Streamlit server on port ${STREAMLIT_PORT}..."
  streamlit run home.py \
    --server.port=${STREAMLIT_PORT:-8501} \
    --server.address=${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}

# If the command is to run both (development only)
elif [ "$1" = "dev" ]; then
  wait_for_postgres
  apply_migrations
  echo "Starting both Django and Streamlit in development mode..."
  python manage.py runserver 0.0.0.0:${DJANGO_PORT:-8000} &
  streamlit run home.py \
    --server.port=${STREAMLIT_PORT:-8501} \
    --server.address=${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}

# If the command is to run a shell
elif [ "$1" = "shell" ]; then
  exec /bin/bash

# If the command is to run a custom command
else
  exec "$@"
fi
