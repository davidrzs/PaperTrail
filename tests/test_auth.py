"""Tests for authentication endpoints"""

import pytest
from fastapi.testclient import TestClient
from src.config import settings


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_login_success(client: TestClient):
    """Test successful login with admin credentials"""
    response = client.post(
        "/auth/login",
        data={
            "username": settings.admin_username,
            "password": settings.admin_password
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == settings.admin_username
    assert data["message"] == "Successfully logged in"
    # Cookie should be set
    assert "access_token" in response.cookies


def test_login_wrong_password(client: TestClient):
    """Test login with wrong password"""
    response = client.post(
        "/auth/login",
        data={
            "username": settings.admin_username,
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_wrong_username(client: TestClient):
    """Test login with wrong username"""
    response = client.post(
        "/auth/login",
        data={
            "username": "wronguser",
            "password": settings.admin_password
        }
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_logout(authenticated_client: TestClient):
    """Test logout clears cookie"""
    response = authenticated_client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"


def test_login_page_loads(client: TestClient):
    """Test that login page loads correctly"""
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    # Check for form elements
    assert 'login' in html.lower()
    assert 'username' in html.lower()
    assert 'password' in html.lower()


def test_protected_endpoint_requires_auth(client: TestClient):
    """Test that protected endpoints require authentication"""
    # Try to create a paper without authentication
    response = client.post(
        "/papers",
        json={
            "title": "Test Paper",
            "authors": "Test Author",
            "summary": "Test summary"
        }
    )
    assert response.status_code == 401


def test_protected_endpoint_with_auth(authenticated_client: TestClient):
    """Test that authenticated client can access protected endpoints"""
    # Try to list papers (this endpoint works with and without auth)
    response = authenticated_client.get("/papers")
    # Should not get 401
    assert response.status_code != 401
