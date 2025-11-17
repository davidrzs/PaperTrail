"""PaperTrail FastAPI application"""

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.database import get_db
from src.embeddings import load_model
from src.routers import auth, papers, tags
from src.auth import require_auth, get_auth_status, get_user_profile
from sqlalchemy.orm import Session

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Personal Paper Reading Tracker with hybrid search",
    debug=settings.debug,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory="src/templates")

# Add global template context
templates.env.globals["user_profile"] = get_user_profile()

# Include routers
app.include_router(auth.router)
app.include_router(papers.router)
app.include_router(tags.router)


@app.on_event("startup")
async def startup_event():
    """Load embedding model on startup"""
    # Note: Database migrations should be run separately via `make migrate`
    # or automatically via docker-compose

    # Load embedding model
    try:
        print("Loading embedding model...")
        load_model()
        print("Embedding model loaded successfully!")
    except Exception as e:
        print(f"Warning: Failed to load embedding model: {e}")
        print("Search functionality will not be available.")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.app_version}


# Template routes
@app.get("/", response_class=HTMLResponse)
async def home():
    """Home page - redirects to papers page"""
    return RedirectResponse(url="/papers", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, _: bool = Depends(require_auth)):
    """Profile/settings page (read-only, shows env config)"""
    return templates.TemplateResponse(
        "settings.html",
        {"request": request}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
