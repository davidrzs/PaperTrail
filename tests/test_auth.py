"""Tests for authentication endpoints"""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_user(client: TestClient):
    """Test user registration"""
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "newpass123",
        "display_name": "New User"
    }

    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert data["display_name"] == user_data["display_name"]
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_username(client: TestClient, test_user: dict):
    """Test registration with duplicate username"""
    from src.config import settings

    user_data = {
        "username": test_user["username"],  # Same username
        "email": "different@example.com",
        "password": "password123"
    }

    response = client.post("/auth/register", json=user_data)

    # In single-user mode, second registration is blocked with 403
    if settings.single_user:
        assert response.status_code == 403
    else:
        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()


def test_register_duplicate_email(client: TestClient, test_user: dict):
    """Test registration with duplicate email"""
    from src.config import settings

    user_data = {
        "username": "differentuser",
        "email": test_user["email"],  # Same email
        "password": "password123"
    }

    response = client.post("/auth/register", json=user_data)

    # In single-user mode, second registration is blocked with 403
    if settings.single_user:
        assert response.status_code == 403
    else:
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()


def test_login_success(client: TestClient, test_user: dict):
    """Test successful login (returns user object and sets cookie)"""
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    # Cookie should be set
    assert "access_token" in response.cookies


def test_login_wrong_password(client: TestClient, test_user: dict):
    """Test login with wrong password"""
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client: TestClient):
    """Test login with non-existent user"""
    response = client.post(
        "/auth/login",
        data={"username": "nonexistent", "password": "password123"}
    )

    assert response.status_code == 401


def test_get_current_user(client: TestClient, test_user: dict):
    """Test getting current user info"""
    response = client.get("/auth/me", headers=test_user["headers"])

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]


def test_get_current_user_unauthorized(client: TestClient):
    """Test getting current user without authentication"""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token(client: TestClient):
    """Test getting current user with invalid token"""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_login_page_loads(client: TestClient):
    """Test that login page loads correctly"""
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    # Check for form elements
    assert 'id="login-form"' in html
    assert 'id="username"' in html
    assert 'id="password"' in html
    assert 'type="password"' in html
    assert "/auth/login" in html
    # Check for link to register page
    assert "/register" in html


def test_register_page_loads(client: TestClient):
    """Test that register page loads correctly"""
    response = client.get("/register")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    # Check for form elements
    assert 'id="register-form"' in html
    assert 'id="username"' in html
    assert 'id="email"' in html
    assert 'id="password"' in html
    assert 'id="display_name"' in html
    assert 'type="email"' in html
    assert 'type="password"' in html
    assert "/auth/register" in html
    # Check for link to login page
    assert "/login" in html


def test_register_and_login_flow(client: TestClient):
    """Test complete registration and login flow via API (with cookies)"""
    # Register a new user
    user_data = {
        "username": "flowuser",
        "email": "flow@example.com",
        "password": "flowpass123",
        "display_name": "Flow User"
    }

    register_response = client.post("/auth/register", json=user_data)
    assert register_response.status_code == 201
    assert "access_token" in register_response.cookies  # Cookie set on registration

    # Verify we can access protected endpoint (cookie sent automatically)
    me_response = client.get("/auth/me")
    assert me_response.status_code == 200
    user_info = me_response.json()
    assert user_info["username"] == user_data["username"]
    assert user_info["email"] == user_data["email"]


def test_update_user_bio(client: TestClient, test_user: dict):
    """Test updating user bio"""
    update_data = {
        "bio": "I created this list for personal paper accountability"
    }

    response = client.put(
        "/auth/me",
        json=update_data,
        headers=test_user["headers"]
    )
    assert response.status_code == 200

    data = response.json()
    assert data["bio"] == update_data["bio"]
    assert data["username"] == test_user["username"]


def test_update_user_display_name_and_bio(client: TestClient, test_user: dict):
    """Test updating both display name and bio"""
    update_data = {
        "display_name": "New Display Name",
        "bio": "Updated bio text"
    }

    response = client.put(
        "/auth/me",
        json=update_data,
        headers=test_user["headers"]
    )
    assert response.status_code == 200

    data = response.json()
    assert data["display_name"] == update_data["display_name"]
    assert data["bio"] == update_data["bio"]


def test_update_user_unauthorized(client: TestClient):
    """Test updating user without authentication"""
    update_data = {
        "bio": "This should fail"
    }

    response = client.put("/auth/me", json=update_data)
    assert response.status_code == 401


def test_settings_page_loads(client: TestClient, test_user: dict):
    """Test that settings page loads with authentication"""
    # With auth (cookie set by test_user fixture), should load settings page
    response = client.get("/settings")
    assert response.status_code == 200
    # Should show settings form
    assert "settings-form" in response.text


def test_user_feed_page_loads(client: TestClient, test_user: dict):
    """Test that user feed page loads correctly"""
    response = client.get(f"/users/{test_user['username']}/feed")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Page shows display name or username
    assert test_user["display_name"] in response.text or test_user["username"] in response.text


def test_user_feed_shows_bio(client: TestClient, test_user: dict):
    """Test that bio is displayed on user feed"""
    # First, set a bio
    bio_text = "I track papers for accountability"
    client.put(
        "/auth/me",
        json={"bio": bio_text},
        headers=test_user["headers"]
    )

    # Now visit the feed page
    response = client.get(f"/users/{test_user['username']}/feed")
    assert response.status_code == 200
    assert bio_text in response.text
