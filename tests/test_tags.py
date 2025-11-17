"""Tests for tag endpoints"""

import pytest
from fastapi.testclient import TestClient


def test_list_tags_empty(authenticated_client: TestClient):
    """Test listing tags when there are no papers"""
    response = authenticated_client.get("/tags")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tags_with_papers(authenticated_client: TestClient):
    """Test listing tags after creating papers"""
    # Create papers with tags
    paper1 = {
        "title": "Paper 1",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["ml", "ai"]
    }
    paper2 = {
        "title": "Paper 2",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["ml", "nlp"]
    }

    authenticated_client.post("/papers", json=paper1)
    authenticated_client.post("/papers", json=paper2)

    # List tags
    response = authenticated_client.get("/tags")
    assert response.status_code == 200

    tags = response.json()
    assert len(tags) == 3  # ml, ai, nlp

    # Check counts
    ml_tag = next(t for t in tags if t["name"] == "ml")
    assert ml_tag["count"] == 2  # Used in 2 papers


def test_tags_are_global(authenticated_client: TestClient):
    """Test that tags are global (not per-user in single-user system)"""
    # Create papers with the same tag name
    paper1 = {
        "title": "Paper 1",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["mytag"]
    }
    paper2 = {
        "title": "Paper 2",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["mytag"]
    }

    authenticated_client.post("/papers", json=paper1)
    authenticated_client.post("/papers", json=paper2)

    # Should see one tag used in 2 papers
    response = authenticated_client.get("/tags")
    tags = response.json()
    assert len(tags) == 1
    assert tags[0]["name"] == "mytag"
    assert tags[0]["count"] == 2  # Used in both papers


def test_autocomplete_tags(authenticated_client: TestClient):
    """Test tag autocomplete"""
    # Create papers with tags
    paper1 = {
        "title": "Paper 1",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["machine-learning", "ml", "transformers"]
    }
    authenticated_client.post("/papers", json=paper1)

    # Autocomplete with prefix "m"
    response = authenticated_client.get("/tags/autocomplete?q=m")
    assert response.status_code == 200

    suggestions = response.json()["suggestions"]
    assert "machine-learning" in suggestions
    assert "ml" in suggestions
    assert "transformers" not in suggestions  # Doesn't start with "m"


def test_autocomplete_tags_unauthorized(client: TestClient):
    """Test that autocomplete requires authentication"""
    response = client.get("/tags/autocomplete?q=test")
    assert response.status_code == 401


def test_tag_case_normalization(authenticated_client: TestClient):
    """Test that tags are normalized to lowercase"""
    paper = {
        "title": "Paper",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["ML", "Transformers", "NLP"]
    }

    response = authenticated_client.post("/papers", json=paper)
    assert response.status_code == 201

    tags = response.json()["tags"]
    tag_names = [t["name"] for t in tags]
    assert "ml" in tag_names
    assert "transformers" in tag_names
    assert "nlp" in tag_names
    assert "ML" not in tag_names  # Should be lowercase


def test_list_tags_unauthorized(client: TestClient):
    """Test that listing tags requires authentication"""
    response = client.get("/tags")
    assert response.status_code == 401
