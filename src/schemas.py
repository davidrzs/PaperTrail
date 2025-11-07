"""Pydantic schemas for request/response validation"""

from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# User schemas
class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    show_heatmap: bool = True


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    show_heatmap: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user responses"""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPublic(BaseModel):
    """Public user info (for other users to see)"""
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    show_heatmap: bool = True

    model_config = ConfigDict(from_attributes=True)


# Authentication schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data stored in JWT token"""
    username: Optional[str] = None


# Tag schemas
class TagBase(BaseModel):
    """Base tag schema"""
    name: str = Field(..., min_length=1, max_length=50)


class TagCreate(TagBase):
    """Schema for creating a tag"""
    pass


class TagResponse(TagBase):
    """Schema for tag responses"""
    id: int
    count: Optional[int] = None  # Number of papers with this tag

    model_config = ConfigDict(from_attributes=True)


# Paper schemas
class PaperBase(BaseModel):
    """Base paper schema"""
    title: str = Field(..., min_length=1, max_length=500)
    authors: str = Field(..., min_length=1, max_length=500)
    arxiv_id: Optional[str] = Field(None, max_length=50)
    doi: Optional[str] = Field(None, max_length=100)
    paper_url: Optional[str] = Field(None, max_length=500)
    abstract: Optional[str] = None  # Optional
    summary: str = Field(..., min_length=1)
    is_private: bool = False
    date_read: Optional[date] = None


class PaperCreate(PaperBase):
    """Schema for creating a paper"""
    tags: List[str] = Field(default_factory=list)


class PaperUpdate(BaseModel):
    """Schema for updating a paper (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    authors: Optional[str] = Field(None, min_length=1, max_length=500)
    arxiv_id: Optional[str] = Field(None, max_length=50)
    doi: Optional[str] = Field(None, max_length=100)
    paper_url: Optional[str] = Field(None, max_length=500)
    abstract: Optional[str] = None
    summary: Optional[str] = Field(None, min_length=1)
    is_private: Optional[bool] = None
    date_read: Optional[date] = None
    tags: Optional[List[str]] = None


class PaperResponse(PaperBase):
    """Schema for paper responses"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = []
    user: UserPublic

    model_config = ConfigDict(from_attributes=True)


class PaperListItem(BaseModel):
    """Simplified paper schema for list views"""
    id: int
    title: str
    authors: str
    summary: str
    is_private: bool
    date_read: Optional[date] = None
    created_at: datetime
    tags: List[TagResponse] = []
    user: UserPublic

    model_config = ConfigDict(from_attributes=True)


class PaperList(BaseModel):
    """Paginated list of papers"""
    papers: List[PaperListItem]
    total: int
    limit: int
    offset: int


# Search schemas
class SearchResult(BaseModel):
    """Individual search result"""
    id: int
    title: str
    authors: str
    summary: str
    score: float  # RRF score
    tags: List[TagResponse] = []
    user: UserPublic

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Search results response"""
    results: List[SearchResult]
    query: str
    total: int
