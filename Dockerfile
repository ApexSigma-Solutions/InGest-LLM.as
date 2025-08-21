# Use Python 3.13 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy poetry files and README
COPY pyproject.toml poetry.lock* README.md ./

# Install dependencies only (not the project itself yet)  
RUN poetry install --no-root

# Copy source code
COPY src/ ./src/

# Install the project itself
RUN poetry install

# Expose port
EXPOSE 8000

# Use Poetry's environment directly
CMD ["poetry", "run", "python", "-m", "uvicorn", "src.ingest_llm_as.main:app", "--host", "0.0.0.0", "--port", "8000"]