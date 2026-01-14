from pydantic import BaseModel, Field, EmailStr
import uuid
from datetime import datetime


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


class CreateUser(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    
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
    email: EmailStr
    password: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePassword123!"
            }
        }
    }


class UpdateUser(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None


class User(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None
    password: str = Field(exclude=True)  
    
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
    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = 0
    
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
    user_id: str
    email: str | None = ""
