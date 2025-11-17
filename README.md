# PaperTrail

[![Tests](https://github.com/davidrzs/PaperTrail/actions/workflows/test.yml/badge.svg)](https://github.com/davidrzs/PaperTrail/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A personal paper reading tracker with hybrid search combining SQLite FTS5 and semantic vector embeddings.

## Features

- **Hybrid Search**: Combines full-text search (SQLite FTS5) with semantic vector search (nomic-embed-text-v1.5) using Reciprocal Rank Fusion
- **Long Context Embeddings**: 8192 token context window handles full paper abstracts without truncation
- **Activity Heatmap**: GitHub-style visualization of reading activity over the last year
- **Single-User System**: Simple deployment with environment-based credentials
- **Privacy Controls**: Public/private paper visibility settings
- **Markdown Support**: Bio and paper content with KaTeX math rendering
- **Tag Management**: Organize papers with autocomplete tag support

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Search**: SQLite FTS5 + Nomic Embed Text v1.5 (768-dim embeddings)
- **Frontend**: Jinja2 templates, vanilla JavaScript
- **Deployment**: Docker, single container with volume persistence

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment variables
cp .env.example .env
# Edit .env and set ADMIN_USERNAME and ADMIN_PASSWORD

# 3. Start the app (auto-initializes database)
make dev

# Visit http://localhost:8000
```

## Development

```bash
# Run tests
make test
uv run pytest tests/ -v

# Run with hot reload
make dev

# Build Docker image
make build

# Run in Docker
make docker-run
```

## Deployment

### Docker (Recommended)

```bash
# Build and run
docker build -t papertrail .
docker run -d \
  -p 8000:8000 \
  -v papertrail_data:/app/data \
  -e ADMIN_USERNAME=your_username \
  -e ADMIN_PASSWORD=your_password \
  -e SECRET_KEY=your_secret_key \
  papertrail
```

### Dokploy

1. Deploy single Dockerfile
2. Add **Volume Mount** (NOT File Mount):
   - Type: "Volume"
   - Container Path: `/app/data`
3. Set environment variables: `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`
4. Database persists in Docker volume automatically

## Environment Variables

Required:
- `ADMIN_USERNAME` - Login username
- `ADMIN_PASSWORD` - Login password (plain text or Argon2 hash)
- `SECRET_KEY` - JWT signing key

Optional:
- `ADMIN_DISPLAY_NAME` - Display name (defaults to username)
- `ADMIN_BIO` - Markdown bio with math support
- `ADMIN_SHOW_HEATMAP` - Show activity heatmap (default: true)
- `DEBUG` - Development mode (default: false)

## Architecture

- **Database**: SQLite with FTS5 virtual table for full-text search
- **Embeddings**: nomic-ai/nomic-embed-text-v1.5 (768-dim, 8192 token context)
- **Search**: Three-stage hybrid search (FTS5 + Vector + RRF)
- **Privacy**: SQL-level filtering for public/private papers

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed developer documentation including:
- Architecture overview
- Database schema and initialization
- Search implementation details
- Testing guidelines
- Deployment configurations

## License

MIT
