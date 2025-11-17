"""Tests for paper CRUD endpoints"""

import pytest
from fastapi.testclient import TestClient


def test_create_paper(authenticated_client: TestClient, sample_paper_data: dict):
    """Test creating a paper"""
    response = authenticated_client.post(
        "/papers",
        json=sample_paper_data
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_paper_data["title"]
    assert data["authors"] == sample_paper_data["authors"]
    assert data["summary"] == sample_paper_data["summary"]
    assert len(data["tags"]) == 3
    assert "id" in data


def test_create_paper_unauthorized(client: TestClient, sample_paper_data: dict):
    """Test creating a paper without authentication"""
    response = client.post("/papers", json=sample_paper_data)
    assert response.status_code == 401


def test_create_paper_without_abstract(authenticated_client: TestClient):
    """Test creating a paper without abstract (optional field)"""
    paper_data = {
        "title": "Test Paper",
        "authors": "Test Author",
        "summary": "Test summary",
        "tags": []
    }

    response = authenticated_client.post(
        "/papers",
        json=paper_data
    )

    assert response.status_code == 201
    assert response.json()["abstract"] is None


def test_list_papers(authenticated_client: TestClient, sample_paper_data: dict):
    """Test listing papers"""
    # Create a paper first
    authenticated_client.post("/papers", json=sample_paper_data)

    # List papers
    response = authenticated_client.get("/papers")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    assert len(data["papers"]) >= 1
    assert data["papers"][0]["title"] == sample_paper_data["title"]


def test_list_papers_with_pagination(authenticated_client: TestClient):
    """Test listing papers with pagination"""
    # Create multiple papers
    for i in range(5):
        paper_data = {
            "title": f"Paper {i}",
            "authors": "Test Author",
            "summary": f"Summary {i}",
            "tags": []
        }
        authenticated_client.post("/papers", json=paper_data)

    # Test pagination
    response = authenticated_client.get("/papers?limit=2&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["papers"]) == 2


def test_list_papers_filter_by_tag(authenticated_client: TestClient):
    """Test filtering papers by tag"""
    # Create papers with different tags
    paper1 = {
        "title": "ML Paper",
        "authors": "Author 1",
        "summary": "Summary 1",
        "tags": ["ml", "ai"]
    }
    paper2 = {
        "title": "NLP Paper",
        "authors": "Author 2",
        "summary": "Summary 2",
        "tags": ["nlp", "transformers"]
    }

    authenticated_client.post("/papers", json=paper1)
    authenticated_client.post("/papers", json=paper2)

    # Filter by tag
    response = authenticated_client.get("/papers?tag=nlp")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["papers"][0]["title"] == "NLP Paper"


def test_get_paper(authenticated_client: TestClient, sample_paper_data: dict):
    """Test getting a single paper"""
    # Create a paper
    create_response = authenticated_client.post(
        "/papers",
        json=sample_paper_data
    )
    paper_id = create_response.json()["id"]

    # Get the paper
    response = authenticated_client.get(f"/papers/{paper_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == paper_id
    assert data["title"] == sample_paper_data["title"]


def test_get_nonexistent_paper(client: TestClient):
    """Test getting a non-existent paper"""
    response = client.get("/papers/99999")
    assert response.status_code == 404


def test_get_private_paper_as_owner(authenticated_client: TestClient):
    """Test getting own private paper"""
    paper_data = {
        "title": "Private Paper",
        "authors": "Test Author",
        "summary": "Private summary",
        "tags": [],
        "is_private": True
    }

    create_response = authenticated_client.post(
        "/papers",
        json=paper_data
    )
    paper_id = create_response.json()["id"]

    # Owner can see their private paper
    response = authenticated_client.get(f"/papers/{paper_id}")
    assert response.status_code == 200


def test_get_private_paper_as_anonymous(authenticated_client: TestClient):
    """Test getting private paper as anonymous user (creates new client without auth)"""
    paper_data = {
        "title": "Private Paper",
        "authors": "Test Author",
        "summary": "Private summary",
        "tags": [],
        "is_private": True
    }

    # Authenticated user creates a private paper
    create_response = authenticated_client.post("/papers", json=paper_data)
    paper_id = create_response.json()["id"]

    # Create a fresh client without authentication cookies
    from fastapi.testclient import TestClient
    from src.main import app
    anonymous_client = TestClient(app)

    # Anonymous user cannot see private paper
    response = anonymous_client.get(f"/papers/{paper_id}")
    assert response.status_code == 404


def test_update_paper(authenticated_client: TestClient, sample_paper_data: dict):
    """Test updating a paper"""
    # Create a paper
    create_response = authenticated_client.post(
        "/papers",
        json=sample_paper_data
    )
    paper_id = create_response.json()["id"]

    # Update the paper
    update_data = {
        "summary": "Updated summary with new insights",
        "tags": ["transformers", "updated"]
    }

    response = authenticated_client.put(
        f"/papers/{paper_id}",
        json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == update_data["summary"]
    assert len(data["tags"]) == 2


def test_update_paper_unauthorized(authenticated_client: TestClient, sample_paper_data: dict):
    """Test updating paper without authentication"""
    # Authenticated user creates a paper
    create_response = authenticated_client.post("/papers", json=sample_paper_data)
    paper_id = create_response.json()["id"]

    # Create a fresh client without authentication cookies
    from fastapi.testclient import TestClient
    from src.main import app
    anonymous_client = TestClient(app)

    # Anonymous user tries to update it
    update_data = {"summary": "Hacked summary"}
    response = anonymous_client.put(f"/papers/{paper_id}", json=update_data)

    assert response.status_code == 401


def test_delete_paper(authenticated_client: TestClient, sample_paper_data: dict):
    """Test deleting a paper"""
    # Create a paper
    create_response = authenticated_client.post(
        "/papers",
        json=sample_paper_data
    )
    paper_id = create_response.json()["id"]

    # Delete the paper
    response = authenticated_client.delete(f"/papers/{paper_id}")

    assert response.status_code == 204

    # Verify it's deleted
    get_response = authenticated_client.get(f"/papers/{paper_id}")
    assert get_response.status_code == 404


def test_delete_paper_unauthorized(authenticated_client: TestClient, sample_paper_data: dict):
    """Test deleting paper without authentication"""
    # Authenticated user creates a paper
    create_response = authenticated_client.post("/papers", json=sample_paper_data)
    paper_id = create_response.json()["id"]

    # Create a fresh client without authentication cookies
    from fastapi.testclient import TestClient
    from src.main import app
    anonymous_client = TestClient(app)

    # Anonymous user tries to delete it
    response = anonymous_client.delete(f"/papers/{paper_id}")

    assert response.status_code == 401


def test_private_papers_not_in_public_list(authenticated_client: TestClient):
    """Test that private papers don't appear in anonymous user lists"""
    # Authenticated user creates a private paper
    private_paper = {
        "title": "Secret Paper",
        "authors": "Test Author",
        "summary": "Secret summary",
        "tags": [],
        "is_private": True
    }

    authenticated_client.post("/papers", json=private_paper)

    # Create a fresh client without authentication cookies
    from fastapi.testclient import TestClient
    from src.main import app
    anonymous_client = TestClient(app)

    # Anonymous user lists papers (should not see the private paper)
    response = anonymous_client.get("/papers")
    assert response.status_code == 200

    papers = response.json()["papers"]
    assert all(p["title"] != "Secret Paper" for p in papers)


def test_new_paper_form_loads(authenticated_client: TestClient):
    """Test that new paper form page loads correctly"""
    response = authenticated_client.get("/papers/new")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "paper-form" in response.text
    assert "Add New Paper" in response.text


def test_new_paper_form_requires_auth(client: TestClient):
    """Test that new paper form requires authentication"""
    response = client.get("/papers/new")
    assert response.status_code == 401
