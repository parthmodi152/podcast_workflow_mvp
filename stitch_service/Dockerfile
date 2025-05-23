# Dockerfile for stitch_service
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Install poetry and dependencies
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false && \
    poetry install --only=main --no-root

# Create directories for final videos
RUN mkdir -p /data/podcast-final && \
    chmod -R 777 /data

# Copy the package source
COPY src ./src/

# Expose the API port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app

# Command to run the FastAPI server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

