"""SQLAlchemy database models"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Table, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.database import Base


# Association table for many-to-many relationship between papers and tags
paper_tags = Table(
    "paper_tags",
    Base.metadata,
    Column("paper_id", Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Paper(Base):
    """Paper model"""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
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
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=paper_tags, back_populates="papers")


class Tag(Base):
    """Tag model"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

    # Relationships
    papers: Mapped[List["Paper"]] = relationship("Paper", secondary=paper_tags, back_populates="tags")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class Embedding(Base):
    """Embedding model for vector search"""

    __tablename__ = "embeddings"

    paper_id: Mapped[int] = mapped_column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    embedding_vector: Mapped[bytes] = mapped_column(Text, nullable=False)  # Stored as blob
    embedding_source: Mapped[str] = mapped_column(String(50), default="abstract_summary", nullable=False)
