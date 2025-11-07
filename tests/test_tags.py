"""Tests for tag endpoints"""

import pytest
from fastapi.testclient import TestClient


def test_list_tags_empty(client: TestClient, test_user: dict):
    """Test listing tags when user has no papers"""
    response = client.get("/tags", headers=test_user["headers"])
    assert response.status_code == 200
    assert response.json() == []


def test_list_tags_with_papers(client: TestClient, test_user: dict):
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

    client.post("/papers", json=paper1, headers=test_user["headers"])
    client.post("/papers", json=paper2, headers=test_user["headers"])

    # List tags
    response = client.get("/tags", headers=test_user["headers"])
    assert response.status_code == 200

    tags = response.json()
    assert len(tags) == 3  # ml, ai, nlp

    # Check counts
    ml_tag = next(t for t in tags if t["name"] == "ml")
    assert ml_tag["count"] == 2  # Used in 2 papers


def test_tags_are_per_user(client: TestClient, test_user: dict, second_user: dict):
    """Test that tags are per-user"""
    # User 1 creates a paper with tag "mytag"
    test_user["login"]()
    paper1 = {
        "title": "Paper 1",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["mytag"]
    }
    client.post("/papers", json=paper1)

    # User 2 creates a paper with tag "mytag" (separate tag)
    second_user["login"]()
    paper2 = {
        "title": "Paper 2",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["mytag"]
    }
    client.post("/papers", json=paper2)

    # Each user should see only their own tag
    test_user["login"]()
    response1 = client.get("/tags")
    tags1 = response1.json()
    assert len(tags1) == 1
    assert tags1[0]["count"] == 1

    second_user["login"]()
    response2 = client.get("/tags")
    tags2 = response2.json()
    assert len(tags2) == 1
    assert tags2[0]["count"] == 1


def test_autocomplete_tags(client: TestClient, test_user: dict):
    """Test tag autocomplete"""
    # Create papers with tags
    paper1 = {
        "title": "Paper 1",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["machine-learning", "ml", "transformers"]
    }
    client.post("/papers", json=paper1, headers=test_user["headers"])

    # Autocomplete with prefix "m"
    response = client.get("/tags/autocomplete?q=m", headers=test_user["headers"])
    assert response.status_code == 200

    suggestions = response.json()["suggestions"]
    assert "machine-learning" in suggestions
    assert "ml" in suggestions
    assert "transformers" not in suggestions  # Doesn't start with "m"


def test_autocomplete_tags_unauthorized(client: TestClient):
    """Test that autocomplete requires authentication"""
    response = client.get("/tags/autocomplete?q=test")
    assert response.status_code == 401


def test_tag_case_normalization(client: TestClient, test_user: dict):
    """Test that tags are normalized to lowercase"""
    paper = {
        "title": "Paper",
        "authors": "Author",
        "summary": "Summary",
        "tags": ["ML", "Transformers", "NLP"]
    }

    response = client.post("/papers", json=paper, headers=test_user["headers"])
    assert response.status_code == 201

    tags = response.json()["tags"]
    tag_names = [t["name"] for t in tags]
    assert "ml" in tag_names
    assert "transformers" in tag_names
    assert "nlp" in tag_names
    assert "ML" not in tag_names  # Should be lowercase
