# ============================================================================
# STAGE 1: Build Stage
# Use a full-featured base image to install build dependencies and compile the
# application environment.
# ============================================================================
FROM python:3.13-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_NO_INTERACTION=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry package manager
RUN pip install poetry

WORKDIR /app

# Configure Poetry to create the virtual environment inside the project directory
RUN poetry config virtualenvs.in-project true

# Copy only the dependency definition files
COPY pyproject.toml poetry.lock* ./

# Install dependencies ONLY.
# The --no-root flag tells Poetry "Just install the dependencies from the lock
# file, don't try to install the project package itself." This is the fix for
# the "Readme not found" error.
RUN poetry install --with dev --no-root


# ============================================================================
# STAGE 2: Final Stage
# Use a minimal, clean base image for the final production container.
# ============================================================================
FROM python:3.13-slim-bookworm AS final

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy the pre-built virtual environment from the builder stage.
COPY --from=builder /app/.venv ./.venv

# Copy the application source code into the final image
COPY src/ ./src/
COPY tests/ ./tests/
# We copy the README now, for the final image, not for the build stage.
COPY README.md .

# Expose the port the application will run on
EXPOSE 8000

# Set the command to run the application using the Python from our virtual env.
CMD ["./.venv/bin/uvicorn", "src.ingest_llm_as.main:app", "--host", "0.0.0.0", "--port", "8000"]

