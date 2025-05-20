# Dockerfile for stitch_service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy only pyproject.toml and poetry.lock (if it exists) to leverage Docker cache
COPY pyproject.toml poetry.lock* ./

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false && poetry install --no-root --without dev

# Copy the rest of the application code
COPY ./src /app/src

# Command to run the Celery worker
CMD celery --workdir=/app -A src.main:celery_app worker -l info -Q stitch_queue

