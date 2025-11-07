"""Tests for user profile endpoints"""

import pytest
from fastapi.testclient import TestClient


def test_get_user_profile(client: TestClient, test_user: dict):
    """Test getting a user profile"""
    response = client.get(f"/users/{test_user['username']}")
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["display_name"] == test_user["display_name"]


def test_get_nonexistent_user_profile(client: TestClient):
    """Test getting a non-existent user profile"""
    response = client.get("/users/nonexistentuser")
    assert response.status_code == 404


def test_get_user_papers(client: TestClient, test_user: dict):
    """Test getting papers from a user"""
    # Create a paper
    paper_data = {
        "title": "Test Paper",
        "authors": "Test Author",
        "summary": "Test summary",
        "tags": []
    }
    client.post("/papers", json=paper_data, headers=test_user["headers"])

    # Get user's papers
    response = client.get(f"/users/{test_user['username']}/papers")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["papers"][0]["title"] == "Test Paper"


def test_user_papers_hide_private_from_others(client: TestClient, test_user: dict, second_user: dict):
    """Test that private papers are hidden from other users"""
    # Create public and private papers as test_user
    test_user["login"]()
    public_paper = {
        "title": "Public Paper",
        "authors": "Author",
        "summary": "Public summary",
        "tags": [],
        "is_private": False
    }
    private_paper = {
        "title": "Private Paper",
        "authors": "Author",
        "summary": "Private summary",
        "tags": [],
        "is_private": True
    }

    client.post("/papers", json=public_paper)
    client.post("/papers", json=private_paper)

    # Other user views the profile
    second_user["login"]()
    response = client.get(f"/users/{test_user['username']}/papers")
    assert response.status_code == 200

    papers = response.json()["papers"]
    assert len(papers) == 1
    assert papers[0]["title"] == "Public Paper"


def test_user_papers_show_private_to_owner(client: TestClient, test_user: dict):
    """Test that owners can see their own private papers"""
    # Create public and private papers
    public_paper = {
        "title": "Public Paper",
        "authors": "Author",
        "summary": "Public summary",
        "tags": [],
        "is_private": False
    }
    private_paper = {
        "title": "Private Paper",
        "authors": "Author",
        "summary": "Private summary",
        "tags": [],
        "is_private": True
    }

    client.post("/papers", json=public_paper, headers=test_user["headers"])
    client.post("/papers", json=private_paper, headers=test_user["headers"])

    # Owner views their own profile
    response = client.get(
        f"/users/{test_user['username']}/papers",
        headers=test_user["headers"]
    )
    assert response.status_code == 200

    papers = response.json()["papers"]
    assert len(papers) == 2  # Both public and private


def test_user_papers_pagination(client: TestClient, test_user: dict):
    """Test pagination for user papers"""
    # Create multiple papers
    for i in range(5):
        paper = {
            "title": f"Paper {i}",
            "authors": "Author",
            "summary": f"Summary {i}",
            "tags": []
        }
        client.post("/papers", json=paper, headers=test_user["headers"])

    # Test pagination
    response = client.get(
        f"/users/{test_user['username']}/papers?limit=2&offset=0"
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["papers"]) == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0
