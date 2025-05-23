# Dockerfile for tts_service
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml ./

# Install poetry and dependencies
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false && \
    poetry install --only=main --no-root

# Create directories for audio files
RUN mkdir -p /data/podcast-audio && \
    chmod -R 777 /data

# Copy the package source
COPY src ./src/

# Expose the API port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app

# Command to run the FastAPI server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

