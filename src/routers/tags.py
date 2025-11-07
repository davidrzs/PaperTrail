"""Tag management endpoints"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.auth import get_current_user
from src.database import get_db
from src.models import Tag, User, Paper, paper_tags
from src.schemas import TagResponse

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=List[TagResponse])
def list_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all tags for the current user with paper counts.

    Args:
        current_user: Authenticated user
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
        .filter(Tag.user_id == current_user.id)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Autocomplete tag suggestions for the current user.

    Args:
        q: Tag prefix to search
        current_user: Authenticated user
        db: Database session

    Returns:
        List of matching tag names
    """
    tags = (
        db.query(Tag.name)
        .filter(
            Tag.user_id == current_user.id,
            Tag.name.like(f"{q.lower()}%")
        )
        .distinct()
        .limit(10)
        .all()
    )

    return {"suggestions": [tag[0] for tag in tags]}
