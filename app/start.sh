#!/bin/bash

echo "Initializing database..."
python init_db.py

echo "Starting Celery worker in background..."
celery -A app.workers.tasks worker --loglevel=info --detach

echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000