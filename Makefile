.PHONY: help test dev build docker-run docker-stop docker-clean

CONTAINER_NAME=papertrail
IMAGE_NAME=papertrail
PORT=8000

help:
	@echo "PaperTrail - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Run locally with uv (auto-initializes database)"
	@echo "  make test             - Run all tests with pytest"
	@echo ""
	@echo "Docker deployment:"
	@echo "  make build            - Build Docker image"
	@echo "  make docker-run       - Run Docker container with volume for database"
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
	@echo "Server will be available at http://localhost:$(PORT)"
	@docker run --rm -it \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		-v papertrail_data:/app/data \
		-e SECRET_KEY="${SECRET_KEY}" \
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
	@echo "Initializing database..."
	@uv run python -c "from src.database import init_db; init_db()"
	@echo "Starting server..."
	uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
