#!/bin/bash

# Выполнение миграций Alembic с помощью manage.py
echo "Running database migrations..."
python manage.py db upgrade

# Запуск основного приложения (используя CMD из Dockerfile)
echo "Starting application..."
exec "$@"