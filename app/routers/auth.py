from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends

from app.models.user import CreateUser, Login, Token
from app.dependencies import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.services.user_service import (
    get_user_service,
    UserService,
    UserAlreadyExistsError,
    InvalidCredentialsError
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: CreateUser,
    user_service: UserService = Depends(get_user_service)
):
    try:
        user = await user_service.create_user(user_data)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
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
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"]
    }
