#!/bin/bash
set -e

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
  echo "Waiting for PostgreSQL..."
  while ! nc -z $DB_HOST $DB_PORT; do
    sleep 0.1
  done
  echo "PostgreSQL is up and running!"
}

# Apply database migrations
apply_migrations() {
  echo "Applying database migrations..."
  python manage.py migrate
}

# If the command is to run Django
if [ "$1" = "django" ]; then
  wait_for_postgres
  apply_migrations
  echo "Starting Django server..."
  python manage.py runserver 0.0.0.0:8000

# If the command is to run Streamlit
elif [ "$1" = "streamlit" ]; then
  wait_for_postgres
  echo "Starting Streamlit server..."
  streamlit run home.py --server.port=8501 --server.address=0.0.0.0

# If the command is to run both (development only)
elif [ "$1" = "dev" ]; then
  wait_for_postgres
  apply_migrations
  echo "Starting both Django and Streamlit in development mode..."
  python manage.py runserver 0.0.0.0:8000 &
  streamlit run home.py --server.port=8501 --server.address=0.0.0.0

# If the command is to run a shell
elif [ "$1" = "shell" ]; then
  exec /bin/bash

# If the command is to run a custom command
else
  exec "$@"
fi
