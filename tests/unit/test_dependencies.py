"""
Unit tests for authentication dependencies.
Tests JWT token creation and verification.
"""
import pytest
from datetime import timedelta
from unittest.mock import Mock
from fastapi import HTTPException
from app.dependencies import (
    create_access_token,
    verify_token,
    SECRET_KEY,
    ALGORITHM
)
from jose import jwt


class TestCreateAccessToken:
    """Tests for JWT token creation."""
    
    def test_create_token_with_data(self):
        """Test creating token with user data."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded
    
    def test_create_token_with_custom_expiry(self):
        """Test creating token with custom expiration."""
        data = {"sub": "user123"}
        expires = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=expires)
        
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "user123"


class TestVerifyToken:
    """Tests for JWT token verification."""
    
    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        result = verify_token(token)
        
        assert result["sub"] == "user123"
        assert result["email"] == "test@example.com"
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token raises error."""
        with pytest.raises(HTTPException) as exc:
            verify_token("invalid.token.here")
        
        assert exc.value.status_code == 401
        assert "Invalid authentication credentials" in exc.value.detail
    
    def test_verify_malformed_token(self):
        """Test verifying a malformed token raises error."""
        with pytest.raises(HTTPException) as exc:
            verify_token("not-a-jwt-token")
        
        assert exc.value.status_code == 401
