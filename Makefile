.PHONY: help test dev migrate migrate-create migrate-down migrate-history seed build docker-run docker-stop docker-clean

CONTAINER_NAME=papertrail
IMAGE_NAME=papertrail
PORT=8000

help:
	@echo "PaperTrail - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Run locally with uv (auto-runs migrations)"
	@echo "  make test             - Run all tests with pytest"
	@echo "  make seed             - Load sample data fixtures (demo user + 8 papers)"
	@echo ""
	@echo "Database migrations:"
	@echo "  make migrate          - Run pending database migrations"
	@echo "  make migrate-create   - Create a new migration file (requires MESSAGE='...')"
	@echo "  make migrate-down     - Rollback one migration"
	@echo "  make migrate-history  - Show migration history"
	@echo ""
	@echo "Docker deployment:"
	@echo "  make build            - Build Docker image"
	@echo "  make docker-run       - Run Docker container (requires DATABASE_URL env var)"
	@echo "  make docker-stop      - Stop Docker container"
	@echo "  make docker-clean     - Remove Docker image and containers"

test:
	@echo "Running tests..."
	uv run pytest tests/ -v

build:
	@echo "Building Docker image..."
	docker build -t $(IMAGE_NAME) .

docker-run:
	@echo "Starting PaperTrail with Docker..."
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "Error: DATABASE_URL environment variable is required"; \
		echo "Example: DATABASE_URL=postgresql://user:pass@host:5432/dbname make docker-run"; \
		exit 1; \
	fi
	@echo "Server will be available at http://localhost:$(PORT)"
	@docker run --rm -it \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		--env-file .env \
		$(IMAGE_NAME)

docker-stop:
	@docker stop $(CONTAINER_NAME) 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) 2>/dev/null || true

docker-clean: docker-stop
	@echo "Cleaning up Docker image..."
	@docker rmi $(IMAGE_NAME) || true
	@echo "Cleaned up!"

dev:
	@echo "Running PaperTrail locally with uv..."
	@echo "Running migrations..."
	@uv run alembic upgrade head
	@echo "Starting server..."
	uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

migrate:
	@echo "Running database migrations..."
	uv run alembic upgrade head
	@echo "Migrations complete!"

migrate-create:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Usage: make migrate-create MESSAGE='description'"; \
		exit 1; \
	fi
	@echo "Creating new migration: $(MESSAGE)"
	@uv run alembic revision -m "$(MESSAGE)"
	@echo "Migration file created in alembic/versions/"
	@echo "Edit the file to add upgrade() and downgrade() logic"

migrate-down:
	@echo "Rolling back one migration..."
	uv run alembic downgrade -1
	@echo "Rollback complete!"

migrate-history:
	@echo "Migration history:"
	@uv run alembic history --verbose

# Load seed data
seed:
	@echo "Loading seed data fixtures..."
	@echo "This will create a demo user and 8 sample papers with embeddings."
	@echo ""
	uv run python -m src.fixtures
	@echo ""
	@echo "Seed data loaded! Start the app with 'make dev' or 'make up'"
