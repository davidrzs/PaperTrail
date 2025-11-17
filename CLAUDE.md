# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PaperTrail is a personal paper reading tracker with hybrid search (SQLite FTS5 + vector embeddings). FastAPI backend serving both API endpoints and HTML templates with Jinja2. Uses SQLite with FTS5 for full-text search and brute-force cosine similarity for semantic vector search using nomic-ai/nomic-embed-text-v1.5, combined via Reciprocal Rank Fusion (RRF). Database initialization via `init_db()` function with automatic FTS5 trigger setup.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Start the app (auto-initializes database)
make dev

# Visit http://localhost:8000
# Login with credentials from .env (ADMIN_USERNAME and ADMIN_PASSWORD)
```

## Development Commands

### Local Development
```bash
# Run locally with hot reload (auto-initializes SQLite database)
make dev

# Run tests
make test
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_auth.py -v

# Run specific test
uv run pytest tests/test_auth.py::test_login_success -v
```

### Docker Deployment
```bash
# Build Docker image
make build

# Run container with persistent volume
make docker-run

# Stop container
make docker-stop

# Clean up Docker image
make docker-clean
```

## Architecture Overview

### Database Layer (`src/database.py`)
- SQLite with file-based storage (`data/papertrail.db`)
- `init_db()` function creates tables and FTS5 virtual table with triggers
- FTS5 virtual table (`papers_fts`) synced via triggers (insert, update, delete)
- `get_db()` dependency provides sessions to FastAPI endpoints
- Foreign keys enabled via pragma on connection

### Database Initialization
No migrations - database initialized via `init_db()` which:
1. Creates all SQLAlchemy tables via `Base.metadata.create_all()`
2. Creates FTS5 virtual table: `CREATE VIRTUAL TABLE papers_fts USING fts5(...)`
3. Sets up triggers to keep FTS5 in sync with papers table
4. Runs automatically on startup (Dockerfile CMD) and via `make dev`

### Search Architecture (`src/search.py`)
Three-stage hybrid search:
1. **SQLite FTS5**: `papers_fts` virtual table with weighted fields (title, authors, abstract, summary)
2. **Vector Search**: Brute-force cosine similarity using numpy on embeddings stored as blobs
3. **Reciprocal Rank Fusion (RRF)**: Combines both results with formula: score = sum(1/(k+rank))

Privacy filtering happens at SQL level in both FTS and vector search. RRF constant `k=60` hardcoded in config.

### Embedding System (`src/embeddings.py`)
- Global `_model` loaded once on startup (heavy operation)
- nomic-ai/nomic-embed-text-v1.5 produces 768-dimensional embeddings
- Supports up to 8192 tokens without truncation (handles long papers)
- Papers embed: abstract + summary concatenated with `search_document:` prefix
- Queries embed: search text with `search_query:` prefix
- Task prefixes required for optimal retrieval performance
- Embeddings stored as bytes blob (numpy array via `tobytes()`)
- Retrieved via `np.frombuffer()` for similarity computation

### Router Structure (`src/routers/`)
- `auth.py` - Login/logout with env credentials, HTTP-only session cookies (JWT)
- `papers.py` - CRUD + search endpoints + HTML template routes
- `tags.py` - Tag management with autocomplete

### Template System
- Base: `src/templates/base.html` with `.content` wrapper (max-width: 1200px, padding: 32px 24px)
- JavaScript-based navigation updates based on auth state
- Global template variable `single_user` controls UI visibility
- Partials: Start with underscore, e.g., `_paper_list.html`, `_paper_form.html`
- ALL CSS: `src/static/css/style.css` (no `<style>` blocks in templates)

### Models (`src/models.py`)
- Paper: Stores paper metadata, abstract, summary, privacy flag
- Tag: Global tags (no user_id), unique by name
- Papers ↔ Tags (many-to-many via `paper_tags` table)
- Embedding: One-to-one with Paper (cascade delete)
- Embedding stores `embedding_vector` as bytes blob (not pgvector type)

## Testing

Test fixtures in `tests/conftest.py`:
- `test_db` - Fresh SQLite database per test, runs `init_db()` to create schema and FTS5
- `client` - TestClient with overridden database dependency
- `test_user` - User with `.login()` helper for session cookies
- `sample_paper_data` - Pre-filled paper data

Tests use session cookies (no manual headers needed after registration/login).

Database file: `data/papertrail_test.db` (auto-created and cleaned up per test)

## Critical Implementation Details

### Paper Creation Flow
When creating a paper (`POST /papers`):
1. Create Paper model and save to DB
2. FTS5 triggers automatically insert into `papers_fts` virtual table
3. Generate embedding from abstract + summary
4. Store embedding as bytes in Embedding table

### Privacy Model
- Papers have `is_private` flag
- Search functions accept `is_authenticated` parameter (boolean)
- FTS search: SQL filter `is_private = 0` for anonymous, all papers if authenticated
- Vector search: Same privacy filtering logic
- Anonymous users see only public papers, authenticated user sees all

### Embedding Storage
Embeddings stored as bytes blob:
```python
# Store: convert numpy array to bytes
embedding_bytes = embedding_vector.tobytes()

# Retrieve: convert bytes back to numpy array
paper_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
```

## Configuration (`src/config.py`)
Environment configuration via `.env`:
- `DATABASE_URL` - SQLite file path (default: `sqlite:///./data/papertrail.db`)
- `SECRET_KEY` - JWT signing key (must change in production)
- `DEBUG` - Development mode flag (default: false)
- `ADMIN_USERNAME` - Single user login username (REQUIRED)
- `ADMIN_PASSWORD` - Single user login password (REQUIRED, can be plain text or Argon2 hash)

All other settings hardcoded in `src/config.py`:
- Embedding model: `nomic-ai/nomic-embed-text-v1.5`
- Token expiry: 30 minutes
- Search limit: 50 results
- RRF constant: k=60
- Rate limit: 60 requests/minute

## Single-User System

This is a true single-user system with no user database table:
- No registration endpoint - credentials configured via environment variables
- Login validates against `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`
- Password can be plain text (not recommended) or Argon2 hash
- All papers belong to the single user (no user_id foreign key)
- Tags are global (no per-user scoping)
- Privacy flag still exists for public/private papers
- Authenticated user sees all papers, anonymous users see only public

Implementation details:
- `src/auth.py`: `authenticate_admin()` validates against env credentials
- `src/routers/auth.py`: Only login/logout endpoints (no registration)
- `src/models.py`: No User model, Paper/Tag have no user_id
- Designed for personal/single-user deployments

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

Cookie settings:
- `httponly=True` - Cannot be accessed by JavaScript
- `max_age=1800` seconds (30 minutes)
- `samesite="lax"` - CSRF protection

## Deployment Notes

### Docker Deployment (Recommended)
Single container with SQLite database in volume:

```bash
# Build and run
make build
make docker-run

# Database persists in Docker volume: papertrail_data
# Volume mounted at: /app/data
```

### Environment Variables for Production
1. `SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. `ADMIN_USERNAME` - Your login username
3. `ADMIN_PASSWORD` - Your login password (can be Argon2 hash for added security)
4. `DEBUG=false`

### Dokploy Deployment
1. Deploy single Dockerfile (no docker-compose needed)
2. Add **Volume Mount** (NOT File Mount - those recreate on each deploy):
   - Type: "Volume" (Docker-managed)
   - Container Path: `/app/data`
   - Volume Name: Auto-generated or use `papertrail-data`
3. Set environment variables in Dokploy UI (SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD)
4. Database persists in Docker volume across deployments

### Production Checklist
1. Set strong `SECRET_KEY` environment variable
2. Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in environment
3. Ensure `DEBUG=false` in `.env`
4. Set `secure=True` for cookies in `src/routers/auth.py` (requires HTTPS)
5. Update CORS origins in `src/main.py` (remove `allow_origins=["*"]`)
6. Ensure volume is configured for `/app/data` to persist database
