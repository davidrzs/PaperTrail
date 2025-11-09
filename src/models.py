"""SQLAlchemy database models"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Table, Date, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from src.database import Base


# Association table for many-to-many relationship between papers and tags
paper_tags = Table(
    "paper_tags",
    Base.metadata,
    Column("paper_id", Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """User model"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    show_heatmap: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    papers: Mapped[List["Paper"]] = relationship("Paper", back_populates="user", cascade="all, delete-orphan")
    tags: Mapped[List["Tag"]] = relationship("Tag", back_populates="user", cascade="all, delete-orphan")


class Paper(Base):
    """Paper model"""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[str] = mapped_column(String(500), nullable=False)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    paper_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Optional
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    date_read: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="papers")
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=paper_tags, back_populates="papers")

    __table_args__ = (
        # GIN index for full-text search using PostgreSQL tsvector
        # This will be created via trigger in the migration
        {},
    )


class Tag(Base):
    """Tag model (per-user tags)"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tags")
    papers: Mapped[List["Paper"]] = relationship("Paper", secondary=paper_tags, back_populates="tags")

    __table_args__ = (
        # Ensure tag names are unique per user
        {"sqlite_autoincrement": True},
    )


class Embedding(Base):
    """Embedding model for vector search using pgvector"""

    __tablename__ = "embeddings"

    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    # Using pgvector - dimension will be set in migration based on model dimension
    embedding_vector = mapped_column(Vector(None), nullable=False)
    embedding_source: Mapped[str] = mapped_column(String(50), default="abstract_summary", nullable=False)

    __table_args__ = (
        # Create index for vector similarity search (using cosine distance)
        Index('embedding_vector_idx', 'embedding_vector', postgresql_using='ivfflat',
              postgresql_with={'lists': 100}, postgresql_ops={'embedding_vector': 'vector_cosine_ops'}),
    )
