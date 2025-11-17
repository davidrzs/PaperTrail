"""Tag management endpoints"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.auth import require_auth
from src.database import get_db
from src.models import Tag, Paper, paper_tags
from src.schemas import TagResponse

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=List[TagResponse])
def list_tags(
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    List all tags with paper counts.

    Args:
        _: Authentication check
        db: Database session

    Returns:
        List of tags with counts
    """
    # Query tags with paper counts
    tags_with_counts = (
        db.query(
            Tag.id,
            Tag.name,
            func.count(paper_tags.c.paper_id).label("count")
        )
        .outerjoin(paper_tags, Tag.id == paper_tags.c.tag_id)
        .group_by(Tag.id, Tag.name)
        .order_by(Tag.name)
        .all()
    )

    return [
        {"id": tag_id, "name": name, "count": count}
        for tag_id, name, count in tags_with_counts
    ]


@router.get("/autocomplete")
def autocomplete_tags(
    q: str = Query(..., min_length=1, description="Tag prefix to search"),
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Autocomplete tag suggestions.

    Args:
        q: Tag prefix to search
        _: Authentication check
        db: Database session

    Returns:
        List of matching tag names
    """
    tags = (
        db.query(Tag.name)
        .filter(Tag.name.like(f"{q.lower()}%"))
        .distinct()
        .limit(10)
        .all()
    )

    return {"suggestions": [tag[0] for tag in tags]}
