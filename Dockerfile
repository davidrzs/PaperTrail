FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files for dependency installation
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies using uv
RUN uv sync --no-dev

# Copy application code
COPY src/ ./src/

# Create data directory for SQLite database (will be volume mounted)
RUN mkdir -p /app/data && chmod 777 /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///./data/papertrail.db

# Download embedding model at build time (optional, can be done at runtime)
# RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')"

# Run database migrations on startup, then start server
CMD uv run python -m src.database init && \
    uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
