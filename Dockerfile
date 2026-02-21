# Command to build the image (as per PRD recommendation):
# docker build -t blk-hacking-ind-ankush-agrawal .

# Build stage
# Selection criteria: Using python-slim for a balance of small size and package compatibility.
FROM python:3.13-slim AS builder

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Final stage
FROM python:3.13-slim

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY app /app/app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"

# Application must run on port 5477 inside the container
EXPOSE 5477

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5477"]
