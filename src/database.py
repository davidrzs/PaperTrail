"""Database connection and session management"""

import sqlite3
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from src.config import settings

# Ensure data directory exists
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug,
)

# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database:
    - Create all tables
    - Set up FTS5 virtual table
    - Create triggers for FTS5 sync
    """
    from src.models import Base  # Import here to avoid circular dependency

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create FTS5 virtual table and triggers
    with engine.connect() as conn:
        # Check if FTS5 table already exists
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='papers_fts'")
        )
        if not result.fetchone():
            # Create FTS5 virtual table
            conn.execute(text("""
                CREATE VIRTUAL TABLE papers_fts USING fts5(
                    title,
                    authors,
                    abstract,
                    summary,
                    content=papers,
                    content_rowid=id
                )
            """))

            # Create triggers to keep FTS in sync
            conn.execute(text("""
                CREATE TRIGGER papers_fts_insert AFTER INSERT ON papers BEGIN
                    INSERT INTO papers_fts(rowid, title, authors, abstract, summary)
                    VALUES (new.id, new.title, new.authors, COALESCE(new.abstract, ''), new.summary);
                END
            """))

            conn.execute(text("""
                CREATE TRIGGER papers_fts_update AFTER UPDATE ON papers BEGIN
                    UPDATE papers_fts
                    SET title=new.title,
                        authors=new.authors,
                        abstract=COALESCE(new.abstract, ''),
                        summary=new.summary
                    WHERE rowid=old.id;
                END
            """))

            conn.execute(text("""
                CREATE TRIGGER papers_fts_delete AFTER DELETE ON papers BEGIN
                    DELETE FROM papers_fts WHERE rowid=old.id;
                END
            """))

            conn.commit()
            print("Database initialized with FTS5 support")
        else:
            print("Database already initialized")
