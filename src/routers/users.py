"""User profile endpoints"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.auth import get_current_user_optional
from src.database import get_db
from src.models import Paper, User
from src.schemas import PaperList, PaperListItem, UserPublic

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="src/templates")


@router.get("/{username}/papers", response_model=PaperList)
def get_user_papers_api(
    username: str,
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get papers from a specific user (API endpoint).

    Returns only public papers unless viewing your own profile.

    Args:
        username: Username
        limit: Number of results
        offset: Pagination offset
        current_user: Optional authenticated user
        db: Database session

    Returns:
        Paginated list of papers

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Build query
    query = db.query(Paper).filter(Paper.user_id == user.id)

    # Filter by visibility
    if current_user and current_user.id == user.id:
        # Viewing own profile - show all papers
        pass
    else:
        # Viewing someone else's profile - show only public papers
        query = query.filter(Paper.is_private == False)

    # Get total count
    total = query.count()

    # Apply pagination and order
    papers = query.order_by(Paper.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "papers": papers,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{username}", response_model=UserPublic)
def get_user_profile_api(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Get user profile by username (API endpoint).

    Args:
        username: Username
        db: Database session

    Returns:
        User profile

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.get("/{username}/feed", response_class=HTMLResponse)
async def get_user_feed_page(
    request: Request,
    username: str,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    User feed page (HTML).

    Shows user's bio and papers.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Build query
    query = db.query(Paper).filter(Paper.user_id == user.id)

    # Filter by visibility
    if current_user and current_user.id == user.id:
        # Viewing own profile - show all papers
        pass
    else:
        # Viewing someone else's profile - show only public papers
        query = query.filter(Paper.is_private == False)

    total = query.count()
    papers = query.order_by(Paper.created_at.desc()).all()

    return templates.TemplateResponse(
        "user_papers.html",
        {
            "request": request,
            "user": user,
            "current_user": current_user,
            "papers": papers,
            "total": total
        }
    )


@router.get("/{username}/search", response_class=HTMLResponse)
async def search_user_papers(
    request: Request,
    username: str,
    q: str = Query("", description="Search query"),
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Search papers for a specific user (HTML fragment for HTMX).
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Build query
    query = db.query(Paper).filter(Paper.user_id == user.id)

    # Filter by visibility
    if current_user and current_user.id == user.id:
        # Viewing own profile - show all papers
        pass
    else:
        # Viewing someone else's profile - show only public papers
        query = query.filter(Paper.is_private == False)

    # If there's a search query, filter papers
    if q.strip():
        search_term = f"%{q}%"
        query = query.filter(
            (Paper.title.ilike(search_term)) |
            (Paper.authors.ilike(search_term)) |
            (Paper.summary.ilike(search_term)) |
            (Paper.abstract.ilike(search_term))
        )

    total = query.count()
    # If searching, don't sort by date (relevance matters more)
    # If not searching, sort by date descending
    if q.strip():
        papers = query.all()
    else:
        papers = query.order_by(Paper.created_at.desc()).all()

    return templates.TemplateResponse(
        "user_papers_list.html",
        {
            "request": request,
            "user": user,
            "current_user": current_user,
            "papers": papers,
            "total": total
        }
    )


@router.get("/{username}/feed.xml")
async def get_user_feed_rss(
    username: str,
    db: Session = Depends(get_db)
):
    """
    User RSS feed (XML).

    Returns RSS 2.0 feed of user's public papers.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get public papers only
    papers = db.query(Paper).filter(
        Paper.user_id == user.id,
        Paper.is_private == False
    ).order_by(Paper.created_at.desc()).limit(50).all()

    # Generate RSS XML
    display_name = user.display_name or user.username
    rss_xml = f'''<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>{display_name}'s Papers - PaperTrail</title>
    <link>http://localhost:8000/users/{username}/feed</link>
    <description>Paper reading list by {display_name}</description>
    <language>en-us</language>
'''

    for paper in papers:
        pub_date = paper.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
        paper_link = paper.paper_url or f"http://localhost:8000/papers/{paper.id}"

        # Escape XML special characters
        title = paper.title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        authors = paper.authors.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        summary = paper.summary.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        tags_str = ', '.join([tag.name for tag in paper.tags]) if paper.tags else ''

        rss_xml += f'''    <item>
        <title>{title}</title>
        <link>{paper_link}</link>
        <description>{summary}</description>
        <author>{authors}</author>
        <pubDate>{pub_date}</pubDate>
        <category>{tags_str}</category>
    </item>
'''

    rss_xml += '''</channel>
</rss>'''

    return Response(content=rss_xml, media_type="application/rss+xml")


@router.get("/{username}/activity")
async def get_user_activity(
    username: str,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get user's reading activity data for heatmap.

    Returns daily paper counts for the last year.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Build query
    query = db.query(Paper).filter(Paper.user_id == user.id)

    # Filter by visibility
    if current_user and current_user.id == user.id:
        # Viewing own profile - show all papers
        pass
    else:
        # Viewing someone else's profile - show only public papers
        query = query.filter(Paper.is_private == False)

    # Get papers with date_read in the last year
    one_year_ago = (datetime.now() - timedelta(days=365)).date()
    papers = query.filter(Paper.date_read >= one_year_ago).all()

    # Aggregate by date
    activity_data = {}
    for paper in papers:
        if paper.date_read:
            date_str = paper.date_read.strftime('%Y-%m-%d')
            activity_data[date_str] = activity_data.get(date_str, 0) + 1

    return activity_data
