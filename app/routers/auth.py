"""
Authentication endpoints for login and registration.
Creates JWT tokens for authenticated users.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import CreateUser, Login, Token
from app.dependencies import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.services.user_service import (
    get_user_service,
    UserService,
    UserAlreadyExistsError,
    InvalidCredentialsError
)
from datetime import timedelta

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: CreateUser,
    user_service: UserService = Depends(get_user_service)
):
    """
    Register a new user and return JWT token.
    
    Passwords are hashed using bcrypt before storage.
    """
    try:
        user = await user_service.create_user(user_data)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@auth_router.post("/login", response_model=Token)
async def login(
    credentials: Login,
    user_service: UserService = Depends(get_user_service)
):
    """
    Login with email and password, returns JWT token.
    
    Passwords are verified using bcrypt.
    """
    try:
        user = await user_service.verify_user_credentials(
            credentials.email,
            credentials.password
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@auth_router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user's information.
    
    This endpoint demonstrates that authentication is working.
    The get_current_user dependency extracts user info from JWT token.
    """
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"]
    }
