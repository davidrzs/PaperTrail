# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PaperTrail is a personal paper reading tracker with hybrid search (FTS5 + vector embeddings). FastAPI backend serving both API endpoints and HTML templates with Jinja2. Uses SQLite with FTS5 for full-text search and Qwen3-Embedding-0.6B for semantic search combined via Reciprocal Rank Fusion (RRF).

## Development Commands

### Using uv (local development)
```bash
# Run locally with hot reload
make dev

# Run tests
make test
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_search.py -v

# Run specific test
uv run pytest tests/test_search.py::test_hybrid_search -v

# Initialize database manually
uv run python -m src.database init
```

### Using Docker
```bash
# Build and run (Ctrl+C to stop)
make run

# Build image only
make build

# Stop and remove container
make stop

# Clean everything
make clean
```

### Database Operations
```bash
# Initialize database with FTS5 tables and triggers
uv run python -m src.database init

# Database is stored in data/papertrail.db
```

## Architecture Overview

### Database Layer (`src/database.py`)
- SQLAlchemy engine with SQLite
- FTS5 virtual table (`papers_fts`) automatically synced via triggers
- Triggers in `init_db()` keep FTS5 in sync with papers table on INSERT/UPDATE/DELETE
- `get_db()` dependency provides sessions to FastAPI endpoints

### Search Architecture (`src/search.py`)
Three-stage hybrid search:
1. FTS5 full-text search on title/authors/abstract/summary (returns ranked paper IDs)
2. Vector cosine similarity search using stored embeddings (returns paper IDs with distances)
3. Reciprocal Rank Fusion (RRF) combines both results with formula: score = sum(1/(k+rank))

Privacy filtering happens at SQL level in both FTS and vector search. RRF constant `k=60` configurable via `settings.rrf_k`.

### Embedding System (`src/embeddings.py`)
- Global `_model` loaded once on startup (heavy operation, ~600MB)
- Papers embed: abstract + summary concatenated
- Query embeds: use `prompt_name="query"` for better retrieval
- Embeddings stored as bytes in database, converted with `np.frombuffer()`

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
- `test_db` - Fresh SQLite database per test with FTS5 setup
- `client` - TestClient with overridden database dependency
- `test_user` - User with `.login()` helper for session cookies
- `sample_paper_data` - Pre-filled paper data

Tests use session cookies (no manual headers needed after registration/login).

## Critical Implementation Details

### Paper Creation Flow
When creating a paper (`POST /papers`):
1. Create Paper model and save to DB
2. FTS5 trigger auto-inserts into `papers_fts`
3. Generate embedding from abstract + summary
4. Store embedding in Embedding table

### Privacy Model
- Papers have `is_private` flag
- Search functions accept `user_id` parameter
- FTS search: SQL filter `(is_private = 0 OR user_id = :user_id)`
- Vector search: SQLAlchemy join filter with same logic
- Anonymous users see only public papers

### Embedding Storage
Embeddings stored as blob:
```python
# Store: embedding.astype(np.float32).tobytes()
# Load: np.frombuffer(blob, dtype=np.float32)
```

## Configuration (`src/config.py`)
Settings loaded from `.env` via pydantic-settings:
- `DATABASE_URL` - Default: `sqlite:///./data/papertrail.db`
- `SECRET_KEY` - JWT signing key (change in production)
- `EMBEDDING_MODEL` - Default: `Qwen/Qwen3-Embedding-0.6B`
- `RRF_K` - RRF constant for hybrid search (default: 60)

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
1. Set `secure=True` for cookies in `src/routers/auth.py` (requires HTTPS)
2. Update CORS origins in `src/main.py` (remove `allow_origins=["*"]`)
3. Set strong `SECRET_KEY` environment variable
4. Set `DEBUG=False`
5. Consider PostgreSQL instead of SQLite
