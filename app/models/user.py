from pydantic import BaseModel, Field, EmailStr
from typing import Optional
import uuid
from datetime import datetime


class UserBase(BaseModel):
    """Base user model with common fields."""
    name: str = Field(..., min_length=2, max_length=100, description="User full name")
    email: EmailStr = Field(..., description="User email address")


class CreateUser(UserBase):
    """Model for creating/registering a new user (used for both /auth/register and /users POST)."""
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "password": "SecurePassword123!"
            }
        }
    }


class Login(BaseModel):
    """Login request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePassword123!"
            }
        }
    }


class UpdateUser(BaseModel):
    """Model for updating user information (all fields optional)."""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="User full name")
    email: Optional[EmailStr] = Field(None, description="User email address")


class User(UserBase):
    """User model (password excluded from responses for security)."""
    id: uuid.UUID = Field(..., description="User unique identifier")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    password: str = Field(exclude=True, description="Password (excluded from responses)")  
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "created_at": "2026-01-10T10:30:00Z",
                "updated_at": None
            }
        }
    }


class Token(BaseModel):
    """JWT token response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: Optional[int] = Field(default=0, description="Token expiration time in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 1800
            }
        }
    }


class TokenData(BaseModel):
    """Token payload data (decoded from JWT)."""
    user_id: str = Field(..., description="User ID from token (standard JWT 'sub' claim)")
    email: Optional[str] = Field(default="", description="User email from token")
