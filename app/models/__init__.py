"""
Models package - organizes all Pydantic models.

User models (user.py):
- CreateUser: For creating/registering users
- Login: For authentication requests
- UpdateUser: For updating user info
- User: User response model
- Token: JWT token response
- TokenData: Token payload data

Health models (health.py):
- HealthDataCreate: For creating health data
- HealthDataResponse: Health data response model
- PaginatedHealthDataResponse: Paginated health data response with cursor
- HealthDataSummary: Health data summary statistics
"""
from .user import CreateUser, User, Login, UpdateUser, UserBase
from .user import Token, TokenData
from .health import HealthDataCreate, HealthDataResponse, PaginatedHealthDataResponse

__all__ = [
    # User models
    "CreateUser",
    "User",
    "Login",
    "UpdateUser",
    "UserBase",
    # Auth models
    "Token",
    "TokenData",
    # Health models
    "HealthDataCreate",
    "HealthDataResponse",
    "PaginatedHealthDataResponse",
]

