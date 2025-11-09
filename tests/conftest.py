"""Pytest configuration and fixtures"""

import os
import sqlite3
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.database import Base, get_db
from src.main import app


# SQLite test database URL
# Override with DATABASE_URL environment variable if needed
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/papertrail_test.db"
)


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a fresh database for each test using SQLite"""

    # Ensure data directory exists
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)

    # Create engine with test database
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Drop FTS5 table first (if exists) since it's not in SQLAlchemy metadata
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS papers_fts"))
        conn.commit()

    # Drop all tables before creating new ones
    Base.metadata.drop_all(bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create FTS5 virtual table and triggers
    with engine.connect() as conn:
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

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        # Clean up: drop FTS5 table first, then all other tables
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS papers_fts"))
            conn.commit()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(test_db: Session) -> TestClient:
    """Create a test client with test database"""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(client: TestClient) -> dict:
    """Create a test user and return user data with login helper"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "display_name": "Test User"
    }

    # Register user (cookie is set automatically)
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    def login_as_user():
        """Helper to re-login as this user (sets cookie)"""
        login_resp = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        assert login_resp.status_code == 200

    return {
        **user_data,
        "id": response.json()["id"],
        "headers": {},  # Keep for backwards compatibility but empty
        "login": login_as_user
    }


@pytest.fixture
def test_user_obj(client: TestClient, test_db: Session):
    """Create a test user and return User object (for search tests)"""
    from src.models import User

    # In single-user mode, check if a user already exists
    if settings.single_user:
        existing_user = test_db.query(User).first()
        if existing_user:
            return existing_user

    user_data = {
        "username": "testuserobj",
        "email": "testuserobj@example.com",
        "password": "testpass123",
        "display_name": "Test User Obj"
    }

    # Register user
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    user_id = response.json()["id"]

    # Fetch and return the User object from database
    user = test_db.query(User).filter(User.id == user_id).first()
    assert user is not None

    return user


@pytest.fixture
def auth_headers(test_user: dict) -> dict:
    """Return authentication headers for test user"""
    return test_user["headers"]


@pytest.fixture
def second_user(client: TestClient) -> dict:
    """Create a second test user with login helper"""
    user_data = {
        "username": "seconduser",
        "email": "second@example.com",
        "password": "secondpass123",
        "display_name": "Second User"
    }

    # Register user (cookie is set automatically and overwrites previous user's cookie)
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    def login_as_user():
        """Helper to re-login as this user (sets cookie)"""
        login_resp = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        assert login_resp.status_code == 200

    return {
        **user_data,
        "id": response.json()["id"],
        "headers": {},  # Keep for backwards compatibility but empty
        "login": login_as_user
    }


@pytest.fixture
def sample_paper_data() -> dict:
    """Sample paper data for testing"""
    return {
        "title": "Attention Is All You Need",
        "authors": "Vaswani et al.",
        "arxiv_id": "1706.03762",
        "doi": "10.48550/arXiv.1706.03762",
        "paper_url": "https://arxiv.org/abs/1706.03762",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        "summary": "Introduces the Transformer architecture using self-attention mechanisms instead of recurrence.",
        "tags": ["transformers", "attention", "nlp"],
        "is_private": False
    }


@pytest.fixture
def db_session(test_db: Session) -> Session:
    """Alias for test_db for consistency in test naming"""
    return test_db


@pytest.fixture
def test_user2(client: TestClient, test_db: Session):
    """Create a second test user and return User object

    In single-user mode, this will skip tests that require a second user.
    """
    from src.models import User

    # Skip creating second user in single-user mode
    if settings.single_user:
        pytest.skip("Second user creation not allowed in single-user mode")

    user_data = {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "testpass123",
        "display_name": "Test User 2"
    }

    # Register user
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    user_id = response.json()["id"]

    # Fetch and return the User object from database
    user = test_db.query(User).filter(User.id == user_id).first()
    assert user is not None

    return user
