# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PaperTrail is a personal paper reading tracker with hybrid search (PostgreSQL FTS + pgvector). FastAPI backend serving both API endpoints and HTML templates with Jinja2. Uses PostgreSQL 18 with tsvector for full-text search, pgvector for semantic vector search using Qwen3-Embedding-0.6B (896 dimensions), combined via Reciprocal Rank Fusion (RRF). Database migrations managed with Alembic.

## Quick Start

Requires PostgreSQL 18+ with pgvector extension. Use a managed service (AWS RDS, DigitalOcean, Supabase, Neon) or install locally.

```bash
# 1. Copy environment file and configure DATABASE_URL
cp .env.example .env
# Edit .env and set DATABASE_URL to your PostgreSQL connection string

# 2. Run migrations
make migrate

# 3. Load sample data (optional but recommended)
make seed

# 4. Start the app
make dev

# Visit http://localhost:8000
# Log in with demo/demo123
```

## Development Commands

### Local Development
```bash
# Run locally with hot reload (requires PostgreSQL with pgvector)
make dev

# Load sample data (demo user + 8 famous ML papers)
make seed

# Run tests
make test
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_search.py -v

# Run specific test
uv run pytest tests/test_search.py::test_hybrid_search -v
```

### Docker Deployment
```bash
# Build Docker image
make build

# Run container (requires .env file with DATABASE_URL)
make docker-run

# Stop container
make docker-stop

# Clean up Docker image
make docker-clean
```

### Database Migrations (Alembic)
```bash
# Run all pending migrations
make migrate

# Create a new migration file (hand-written)
make migrate-create MESSAGE="add new field to users"

# Rollback one migration
make migrate-down

# Show migration history
make migrate-history

# Direct Alembic commands
uv run alembic upgrade head        # Apply all migrations
uv run alembic downgrade -1        # Rollback one migration
uv run alembic current             # Show current revision
uv run alembic history --verbose   # Show detailed history
```

### Loading Seed Data (Fixtures)
```bash
# Load sample data for development
make seed

# Creates:
#   - Demo user (username: demo, password: demo123)
#   - 8 famous ML/AI papers (Attention Is All You Need, BERT, GPT-3, etc.)
#   - Tags for each paper
#   - Embeddings for semantic search

# Custom fixtures file
uv run python -m src.fixtures path/to/custom_fixtures.json

# Safe to run multiple times - skips existing users/papers
```

Fixtures are defined in `fixtures/seed_data.json`. The loader (`src/fixtures.py`):
- Creates users with hashed passwords
- Creates papers with associated tags
- Generates embeddings for each paper
- Skips duplicates on re-run

## Architecture Overview

### Database Layer (`src/database.py`)
- SQLAlchemy engine with PostgreSQL 18
- Alembic for schema migrations (`alembic/versions/`)
- `get_db()` dependency provides sessions to FastAPI endpoints
- Connection pooling with `pool_pre_ping=True` for reliability

### Migration System (`alembic/`)
- Hand-written migrations (not auto-generated) for full control
- Initial migration (`001_initial_schema.py`) creates:
  - All tables with proper indexes
  - pgvector extension
  - Generated column `search_vector` (tsvector) with weighted FTS
  - GIN index for full-text search
  - IVFFlat index for vector similarity (cosine distance)
- Migrations run automatically via `make dev` or at Docker startup
- New migrations created with `make migrate-create MESSAGE="..."`

### Search Architecture (`src/search.py`)
Three-stage hybrid search:
1. PostgreSQL FTS using `search_vector` column (generated tsvector with weighted fields: title=A, authors=B, abstract=C, summary=D)
2. pgvector cosine similarity search using `<=>` operator with IVFFlat index
3. Reciprocal Rank Fusion (RRF) combines both results with formula: score = sum(1/(k+rank))

Privacy filtering happens at SQL level in both FTS and vector search. RRF constant `k=60` hardcoded in config.

### Embedding System (`src/embeddings.py`)
- Global `_model` loaded once on startup (heavy operation, ~600MB)
- Qwen3-Embedding-0.6B produces 896-dimensional vectors
- Papers embed: abstract + summary concatenated
- Query embeds: use `prompt_name="query"` for better retrieval
- Embeddings stored as pgvector type, queried with native operators

### Router Structure (`src/routers/`)
- `auth.py` - HTTP-only session cookies (JWT stored in cookie)
- `papers.py` - CRUD + search endpoints + HTML template routes
- `tags.py` - Per-user tags with autocomplete
- `users.py` - User profiles and RSS feeds

### Template System
- Base: `src/templates/base.html` with `.content` wrapper (max-width: 1200px, padding: 32px 24px)
- Partials: Start with underscore, e.g., `_paper_list.html`, `_paper_form.html`
- ALL CSS: `src/static/css/style.css` (no `<style>` blocks in templates)

### Models (`src/models.py`)
- User → Papers (one-to-many, cascade delete)
- User → Tags (one-to-many, cascade delete)
- Papers ↔ Tags (many-to-many via `paper_tags` table)
- Paper → Embedding (one-to-one, cascade delete)

## Testing

Test fixtures in `tests/conftest.py`:
- `test_db` - Fresh PostgreSQL database per test, runs Alembic migrations via `alembic upgrade head`
- `client` - TestClient with overridden database dependency
- `test_user` - User with `.login()` helper for session cookies
- `sample_paper_data` - Pre-filled paper data

Tests use session cookies (no manual headers needed after registration/login).

Requires `TEST_DATABASE_URL` environment variable or uses default `postgresql://postgres:postgres@localhost:5432/papertrail_test`.
Ensure PostgreSQL is running and accessible before running tests.

## Critical Implementation Details

### Paper Creation Flow
When creating a paper (`POST /papers`):
1. Create Paper model and save to DB
2. Generated `search_vector` column auto-updates (PostgreSQL generated column)
3. Generate embedding from abstract + summary
4. Store embedding in Embedding table (pgvector type)

### Privacy Model
- Papers have `is_private` flag
- Search functions accept `user_id` parameter
- FTS search: SQL filter `(is_private = false OR user_id = :user_id)`
- Vector search: JOIN with papers table applying same filter
- Anonymous users see only public papers

### Embedding Storage
Embeddings stored as pgvector type:
```python
# Store: embedding_vector column accepts list directly
query_vector = embedding.tolist()

# Query with cosine distance operator
SELECT embedding_vector <=> :query_vector AS distance
FROM embeddings
ORDER BY distance
```

## Configuration (`src/config.py`)
Minimal environment configuration - only 3 settings via `.env`:
- `DATABASE_URL` - PostgreSQL connection string (default: `postgresql://papertrail:papertrail_dev_password@localhost:5432/papertrail`)
- `SECRET_KEY` - JWT signing key (must change in production, generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `DEBUG` - Development mode flag (default: false)

All other settings hardcoded in `src/config.py`:
- Embedding model: `Qwen/Qwen3-Embedding-0.6B`
- Token expiry: 30 minutes
- Search limit: 50 results
- RRF constant: k=60
- Rate limit: 60 requests/minute

## Frontend Conventions

### Styling
ALL CSS in `src/static/css/style.css`. No `<style>` blocks or inline styles (except `display:none` or JS-generated HTML).

### Template Partials
- `_paper_list.html` - Requires: `papers`, `current_user` (optional), `show_actions`
- `_paper_form.html` - Requires: `paper` (optional, if present = edit mode)

Always use partials for repeated UI components. Do not duplicate HTML.

### Layout
Use `.content` wrapper from `base.html`. Do not create custom wrappers with different max-width or padding.

## Authentication
HTTP-only session cookies (JWT in cookie). No client-side token management. Cookies sent automatically with requests.

## Deployment Notes
Before production:
1. Set strong `SECRET_KEY` environment variable (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
2. Set `DATABASE_URL` to your managed PostgreSQL 18+ service with pgvector extension
3. Ensure `DEBUG=false` in `.env`
4. Set `secure=True` for cookies in `src/routers/auth.py` (requires HTTPS)
5. Update CORS origins in `src/main.py` (remove `allow_origins=["*"]`)
6. Run migrations: `make migrate` or `alembic upgrade head`
7. Consider recreating IVFFlat index AFTER populating significant data with optimal `lists` parameter (sqrt of number of rows)
