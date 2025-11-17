"""Paper CRUD endpoints"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.auth import require_auth, get_auth_status
from src.database import get_db
from src.embeddings import generate_paper_embedding
from src.models import Embedding, Paper, Tag
from src.schemas import PaperCreate, PaperList, PaperListItem, PaperResponse, PaperUpdate, SearchResponse, SearchResult
from src.search import hybrid_search

router = APIRouter(prefix="/papers", tags=["papers"])
templates = Jinja2Templates(directory="src/templates")


def get_or_create_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    """
    Get existing tags or create new ones.

    Args:
        db: Database session
        tag_names: List of tag names

    Returns:
        List of Tag objects
    """
    tags = []
    for name in tag_names:
        name = name.strip().lower()
        if not name:
            continue

        # Try to find existing tag
        tag = db.query(Tag).filter(Tag.name == name).first()

        if not tag:
            # Create new tag
            tag = Tag(name=name)
            db.add(tag)

        tags.append(tag)

    return tags


@router.post("", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
def create_paper(
    paper_data: PaperCreate,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Create a new paper.

    Args:
        paper_data: Paper creation data
        _: Authentication check
        db: Database session

    Returns:
        Created paper object
    """
    # Create paper
    db_paper = Paper(
        title=paper_data.title,
        authors=paper_data.authors,
        arxiv_id=paper_data.arxiv_id,
        doi=paper_data.doi,
        paper_url=paper_data.paper_url,
        abstract=paper_data.abstract,
        summary=paper_data.summary,
        is_private=paper_data.is_private,
        date_read=paper_data.date_read
    )

    # Handle tags
    if paper_data.tags:
        db_paper.tags = get_or_create_tags(db, paper_data.tags)

    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)

    # Generate and store embedding
    try:
        import numpy as np
        embedding_vector = generate_paper_embedding(db_paper.abstract, db_paper.summary)

        # Convert numpy array to bytes for storage
        embedding_blob = embedding_vector.astype(np.float32).tobytes()

        db_embedding = Embedding(
            paper_id=db_paper.id,
            embedding_vector=embedding_blob,
            embedding_source="abstract_summary"
        )
        db.add(db_embedding)
        db.commit()
    except Exception as e:
        # Log error but don't fail the paper creation
        print(f"Warning: Failed to generate embedding for paper {db_paper.id}: {e}")

    return db_paper


@router.get("")
def list_papers(
    request: Request,
    tag: Optional[str] = Query(None, description="Filter by tag name"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    is_authenticated: bool = Depends(get_auth_status),
    db: Session = Depends(get_db)
):
    """
    List papers with optional filters.

    Returns public papers for anonymous users, all papers for authenticated user.
    Returns HTML for browser requests, JSON for API requests.

    Args:
        request: FastAPI request object
        tag: Optional filter by tag name
        limit: Number of results (1-100)
        offset: Pagination offset
        is_authenticated: Whether user is authenticated
        db: Database session

    Returns:
        HTML or JSON paginated list of papers
    """
    # Build query
    query = db.query(Paper)

    # Filter by visibility
    if not is_authenticated:
        # Anonymous users see only public papers
        query = query.filter(Paper.is_private == False)

    # Filter by tag
    if tag:
        query = query.join(Paper.tags).filter(Tag.name == tag.lower())

    # Get total count
    total = query.count()

    # Apply pagination and order
    papers = query.order_by(Paper.created_at.desc()).offset(offset).limit(limit).all()

    # Check if this is a browser request (HTML) or API request (JSON)
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        # Return HTML page
        filter_info = f"Tag: {tag}" if tag else "All Papers"
        return templates.TemplateResponse(
            "papers_list.html",
            {
                "request": request,
                "papers": papers,
                "total": total,
                "filter_info": filter_info,
                "tag": tag,
                "is_authenticated": is_authenticated
            }
        )
    else:
        # Return JSON for API
        return {
            "papers": papers,
            "total": total,
            "limit": limit,
            "offset": offset
        }


@router.get("/search")
def search_papers(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    is_authenticated: bool = Depends(get_auth_status),
    db: Session = Depends(get_db)
):
    """
    Hybrid search for papers using FTS5 + vector similarity with RRF.

    Searches across public papers (or all papers if authenticated).
    Returns HTML for HTMX requests, JSON for API calls.

    Args:
        request: FastAPI request object
        q: Search query
        limit: Maximum number of results
        is_authenticated: Whether user is authenticated
        db: Database session

    Returns:
        Search results with RRF scores (HTML or JSON)
    """
    # Perform hybrid search
    results = hybrid_search(db, q, limit=limit, is_authenticated=is_authenticated)

    # Fetch paper details
    paper_ids = [paper_id for paper_id, score in results]
    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()

    # Create a map of paper_id to score
    score_map = {paper_id: score for paper_id, score in results}

    # Build response maintaining order from search results
    search_results = []
    for paper in papers:
        search_results.append({
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "summary": paper.summary,
            "score": score_map[paper.id],
            "tags": [{"id": t.id, "name": t.name} for t in paper.tags]
        })

    # Sort by score to maintain order
    search_results.sort(key=lambda x: x["score"], reverse=True)

    # Check if this is an HTMX request (returns HTML) or API request (returns JSON)
    if request.headers.get("HX-Request"):
        # Return HTML fragment for HTMX
        return templates.TemplateResponse(
            "search_results.html",
            {
                "request": request,
                "results": search_results,
                "query": q,
                "total": len(search_results)
            }
        )
    else:
        # Return JSON for API
        return {
            "results": search_results,
            "query": q,
            "total": len(search_results)
        }


@router.get("/new", response_class=HTMLResponse)
async def new_paper_form(
    request: Request,
    _: bool = Depends(require_auth)
):
    """
    New paper form page (HTML).

    Requires authentication.
    """
    return templates.TemplateResponse(
        "paper_form.html",
        {"request": request, "is_authenticated": True}
    )


@router.get("/{paper_id}/edit", response_class=HTMLResponse)
async def edit_paper_form(
    request: Request,
    paper_id: int,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Edit paper form page (HTML).

    Requires authentication.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    return templates.TemplateResponse(
        "paper_edit.html",
        {"request": request, "is_authenticated": True, "paper": paper}
    )


@router.get("/{paper_id}")
def get_paper(
    request: Request,
    paper_id: int,
    is_authenticated: bool = Depends(get_auth_status),
    db: Session = Depends(get_db)
):
    """
    Get a single paper by ID.

    Returns HTML for browser requests, JSON for API calls.

    Args:
        request: FastAPI request object
        paper_id: Paper ID
        is_authenticated: Whether user is authenticated
        db: Database session

    Returns:
        Paper object (JSON) or HTML page

    Raises:
        HTTPException: If paper not found or not authorized
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    # Check visibility
    if paper.is_private and not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    # Check if browser request (Accept: text/html) vs API request
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and "application/json" not in accept_header:
        # Return HTML for browser
        return templates.TemplateResponse(
            "paper_detail.html",
            {
                "request": request,
                "paper": paper,
                "is_authenticated": is_authenticated
            }
        )
    else:
        # Return JSON for API
        return paper


@router.put("/{paper_id}", response_model=PaperResponse)
def update_paper(
    paper_id: int,
    paper_data: PaperUpdate,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update a paper.

    Requires authentication.

    Args:
        paper_id: Paper ID
        paper_data: Paper update data
        _: Authentication check
        db: Database session

    Returns:
        Updated paper object

    Raises:
        HTTPException: If paper not found
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    # Update fields
    update_data = paper_data.model_dump(exclude_unset=True)

    # Handle tags separately
    if "tags" in update_data:
        tag_names = update_data.pop("tags")
        if tag_names is not None:
            paper.tags = get_or_create_tags(db, tag_names)

    # Update other fields
    for field, value in update_data.items():
        setattr(paper, field, value)

    db.commit()
    db.refresh(paper)

    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: int,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Delete a paper.

    Requires authentication.

    Args:
        paper_id: Paper ID
        _: Authentication check
        db: Database session

    Raises:
        HTTPException: If paper not found
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )

    db.delete(paper)
    db.commit()

    return None
