# Dockerfile for script_service
FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only pyproject.toml and poetry.lock (if it exists) to leverage Docker cache
COPY pyproject.toml poetry.lock* ./

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false && poetry install --no-root --without dev

# Copy the rest of the application code
COPY ./src /app/src

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

