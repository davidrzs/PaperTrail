FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files for dependency installation
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code and migrations
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run database migrations on startup, then start server
CMD uv run alembic upgrade head && \
    uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
