"""Tests for paper CRUD endpoints"""

import pytest
from fastapi.testclient import TestClient


def test_create_paper(client: TestClient, test_user: dict, sample_paper_data: dict):
    """Test creating a paper"""
    response = client.post(
        "/papers",
        json=sample_paper_data,
        headers=test_user["headers"]
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_paper_data["title"]
    assert data["authors"] == sample_paper_data["authors"]
    assert data["summary"] == sample_paper_data["summary"]
    assert len(data["tags"]) == 3
    assert data["user_id"] == test_user["id"]
    assert "id" in data


def test_create_paper_unauthorized(client: TestClient, sample_paper_data: dict):
    """Test creating a paper without authentication"""
    response = client.post("/papers", json=sample_paper_data)
    assert response.status_code == 401


def test_create_paper_without_abstract(client: TestClient, test_user: dict):
    """Test creating a paper without abstract (optional field)"""
    paper_data = {
        "title": "Test Paper",
        "authors": "Test Author",
        "summary": "Test summary",
        "tags": []
    }

    response = client.post(
        "/papers",
        json=paper_data,
        headers=test_user["headers"]
    )

    assert response.status_code == 201
    assert response.json()["abstract"] is None


def test_list_papers(client: TestClient, test_user: dict, sample_paper_data: dict):
    """Test listing papers"""
    # Create a paper first
    client.post("/papers", json=sample_paper_data, headers=test_user["headers"])

    # List papers
    response = client.get("/papers")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    assert len(data["papers"]) >= 1
    assert data["papers"][0]["title"] == sample_paper_data["title"]


def test_list_papers_with_pagination(client: TestClient, test_user: dict):
    """Test listing papers with pagination"""
    # Create multiple papers
    for i in range(5):
        paper_data = {
            "title": f"Paper {i}",
            "authors": "Test Author",
            "summary": f"Summary {i}",
            "tags": []
        }
        client.post("/papers", json=paper_data, headers=test_user["headers"])

    # Test pagination
    response = client.get("/papers?limit=2&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["papers"]) == 2


def test_list_papers_filter_by_tag(client: TestClient, test_user: dict):
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

    client.post("/papers", json=paper1, headers=test_user["headers"])
    client.post("/papers", json=paper2, headers=test_user["headers"])

    # Filter by tag
    response = client.get("/papers?tag=nlp")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["papers"][0]["title"] == "NLP Paper"


def test_get_paper(client: TestClient, test_user: dict, sample_paper_data: dict):
    """Test getting a single paper"""
    # Create a paper
    create_response = client.post(
        "/papers",
        json=sample_paper_data,
        headers=test_user["headers"]
    )
    paper_id = create_response.json()["id"]

    # Get the paper
    response = client.get(f"/papers/{paper_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == paper_id
    assert data["title"] == sample_paper_data["title"]


def test_get_nonexistent_paper(client: TestClient):
    """Test getting a non-existent paper"""
    response = client.get("/papers/99999")
    assert response.status_code == 404


def test_get_private_paper_as_owner(client: TestClient, test_user: dict):
    """Test getting own private paper"""
    paper_data = {
        "title": "Private Paper",
        "authors": "Test Author",
        "summary": "Private summary",
        "tags": [],
        "is_private": True
    }

    create_response = client.post(
        "/papers",
        json=paper_data,
        headers=test_user["headers"]
    )
    paper_id = create_response.json()["id"]

    # Owner can see their private paper
    response = client.get(f"/papers/{paper_id}", headers=test_user["headers"])
    assert response.status_code == 200


def test_get_private_paper_as_non_owner(client: TestClient, test_user: dict, second_user: dict):
    """Test getting someone else's private paper"""
    paper_data = {
        "title": "Private Paper",
        "authors": "Test Author",
        "summary": "Private summary",
        "tags": [],
        "is_private": True
    }

    # test_user creates a private paper (cookie is set from test_user fixture)
    test_user["login"]()  # Ensure test_user is logged in
    create_response = client.post("/papers", json=paper_data)
    paper_id = create_response.json()["id"]

    # Switch to second_user - they cannot see private paper
    second_user["login"]()
    response = client.get(f"/papers/{paper_id}")
    assert response.status_code == 404


def test_update_paper(client: TestClient, test_user: dict, sample_paper_data: dict):
    """Test updating a paper"""
    # Create a paper
    create_response = client.post(
        "/papers",
        json=sample_paper_data,
        headers=test_user["headers"]
    )
    paper_id = create_response.json()["id"]

    # Update the paper
    update_data = {
        "summary": "Updated summary with new insights",
        "tags": ["transformers", "updated"]
    }

    response = client.put(
        f"/papers/{paper_id}",
        json=update_data,
        headers=test_user["headers"]
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == update_data["summary"]
    assert len(data["tags"]) == 2


def test_update_paper_unauthorized(client: TestClient, test_user: dict, second_user: dict, sample_paper_data: dict):
    """Test updating someone else's paper"""
    # User 1 creates a paper
    test_user["login"]()
    create_response = client.post("/papers", json=sample_paper_data)
    paper_id = create_response.json()["id"]

    # User 2 tries to update it
    second_user["login"]()
    update_data = {"summary": "Hacked summary"}
    response = client.put(f"/papers/{paper_id}", json=update_data)

    assert response.status_code == 403


def test_delete_paper(client: TestClient, test_user: dict, sample_paper_data: dict):
    """Test deleting a paper"""
    # Create a paper
    create_response = client.post(
        "/papers",
        json=sample_paper_data,
        headers=test_user["headers"]
    )
    paper_id = create_response.json()["id"]

    # Delete the paper
    response = client.delete(
        f"/papers/{paper_id}",
        headers=test_user["headers"]
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/papers/{paper_id}")
    assert get_response.status_code == 404


def test_delete_paper_unauthorized(client: TestClient, test_user: dict, second_user: dict, sample_paper_data: dict):
    """Test deleting someone else's paper"""
    # User 1 creates a paper
    test_user["login"]()
    create_response = client.post("/papers", json=sample_paper_data)
    paper_id = create_response.json()["id"]

    # User 2 tries to delete it
    second_user["login"]()
    response = client.delete(f"/papers/{paper_id}")

    assert response.status_code == 403


def test_private_papers_not_in_public_list(client: TestClient, test_user: dict, second_user: dict):
    """Test that private papers don't appear in public lists"""
    # User 1 creates a private paper
    test_user["login"]()
    private_paper = {
        "title": "Secret Paper",
        "authors": "Test Author",
        "summary": "Secret summary",
        "tags": [],
        "is_private": True
    }

    client.post("/papers", json=private_paper)

    # User 2 lists papers (should not see the private paper)
    second_user["login"]()
    response = client.get("/papers")
    assert response.status_code == 200

    papers = response.json()["papers"]
    assert all(p["title"] != "Secret Paper" for p in papers)



def test_new_paper_form_loads(client: TestClient, test_user: dict):
    """Test that new paper form page loads correctly"""
    response = client.get("/papers/new", headers=test_user["headers"])
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "paper-form" in response.text
    assert "Add New Paper" in response.text


def test_new_paper_form_requires_auth(client: TestClient):
    """Test that new paper form requires authentication"""
    response = client.get("/papers/new")
    assert response.status_code == 401

