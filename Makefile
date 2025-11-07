.PHONY: help test run stop clean build dev

CONTAINER_NAME=papertrail
IMAGE_NAME=papertrail
PORT=8000

help:
	@echo "PaperTrail - Available commands:"
	@echo "  make test    - Run all tests with pytest"
	@echo "  make run     - Build and start Docker container (Ctrl+C to stop)"
	@echo "  make build   - Build Docker image"
	@echo "  make clean   - Remove Docker image"
	@echo "  make dev     - Run locally with uv (for development)"

test:
	@echo "Running tests..."
	uv run pytest tests/ -v

build:
	@echo "Building Docker image..."
	docker build -t $(IMAGE_NAME) .

run: build stop
	@echo "Starting PaperTrail with Docker..."
	@echo "Press Ctrl+C to stop"
	@echo "Server will be available at http://localhost:$(PORT)"
	@mkdir -p data
	@chmod 777 data
	@docker run --rm -it \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8000 \
		-v $(PWD)/data:/app/data:Z \
		-e DATABASE_URL=sqlite:///./data/papertrail.db \
		-e SECRET_KEY=change-me-in-production \
		$(IMAGE_NAME)

stop:
	@docker stop $(CONTAINER_NAME) 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) 2>/dev/null || true

clean: stop
	@echo "Cleaning up Docker container and data..."
	@docker rmi $(IMAGE_NAME) || true
	@echo "Cleaned up!"

dev:
	@echo "Running PaperTrail locally with uv..."
	@echo "Initializing database..."
	@mkdir -p data
	uv run python -m src.database init
	@echo "Starting server..."
	uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
