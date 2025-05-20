# Dockerfile for voice_service
FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only pyproject.toml and poetry.lock (if it exists) to leverage Docker cache
COPY pyproject.toml poetry.lock* ./

# Install dependencies using Poetry
# --no-root: Do not install the project itself as editable, install dependencies only
# --without dev: Skip development dependencies
RUN poetry config virtualenvs.create false && poetry install --no-root --without dev

# Install additional required packages
RUN pip install python-multipart

# Copy the rest of the application code
COPY ./src /app/src

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

