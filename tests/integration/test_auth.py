"""
Integration tests for authentication endpoints.
Tests the full request/response cycle with database.
"""
import pytest


class TestRegister:
    """Tests for POST /auth/register endpoint."""
    
    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "name": "New User",
            "email": "newuser@example.com",
            "password": "securepassword123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
    
    def test_register_duplicate_email(self, client):
        """Test registration with existing email fails."""
        # Register first user
        client.post("/auth/register", json={
            "name": "First User",
            "email": "duplicate@example.com",
            "password": "password123"
        })
        
        # Try to register with same email
        response = client.post("/auth/register", json={
            "name": "Second User",
            "email": "duplicate@example.com",
            "password": "password456"
        })
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post("/auth/register", json={
            "name": "Test User",
            "email": "not-an-email",
            "password": "password123"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self, client):
        """Test registration with password too short."""
        response = client.post("/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "short"
        })
        
        assert response.status_code == 422
    
    def test_register_missing_name(self, client):
        """Test registration without name fails."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login endpoint."""
    
    def test_login_success(self, client, registered_user):
        """Test successful login."""
        response = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
    
    def test_login_wrong_password(self, client, registered_user):
        """Test login with wrong password fails."""
        response = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user fails."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 401
    
    def test_login_missing_email(self, client):
        """Test login without email fails."""
        response = client.post("/auth/login", json={
            "password": "password123"
        })
        
        assert response.status_code == 422


class TestGetCurrentUser:
    """Tests for GET /auth/me endpoint."""
    
    def test_get_current_user_success(self, client, registered_user):
        """Test getting current user with valid token."""
        response = client.get("/auth/me", headers=registered_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == registered_user["user_id"]
        assert data["email"] == registered_user["email"]
    
    def test_get_current_user_no_token(self, client):
        """Test getting current user without token fails."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401  # 401 Unauthorized (no token) is correct
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token fails."""
        response = client.get("/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        
        assert response.status_code == 401
