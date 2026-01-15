import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import Depends
from google.cloud.firestore import Client
from google.cloud.firestore_v1.base_query import FieldFilter
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.models.user import CreateUser, User


class UserNotFoundError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserService:
    """Service for user-related operations."""
    
    COLLECTION_NAME = "users"
    
    def __init__(self, db: Client):
        self.db = db
        self.collection = self.db.collection(self.COLLECTION_NAME)
    
    async def create_user(self, user_data: CreateUser) -> User:
        """Create a new user with hashed password."""
        email_query = self.collection.where(filter=FieldFilter("email", "==", user_data.email)).limit(1).stream()
        docs = await run_in_threadpool(list, email_query)
        if docs:
            raise UserAlreadyExistsError(f"Email {user_data.email} already registered")
        
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt(rounds=4))
        password_hash = password_hash.decode('utf-8')
        user_doc = {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "password_hash": password_hash,
            "created_at": now,
        }
        
        await run_in_threadpool(self.collection.document(user_id).set, user_doc)
        
        return User(
            id=uuid.UUID(user_id),
            name=user_data.name,
            email=user_data.email,
            created_at=now,
            password=""
        )
    
    async def get_user_by_email(self, email: str) -> dict | None:
        """Get user by email address."""
        query = self.collection.where(filter=FieldFilter("email", "==", email)).limit(1).stream()
        docs = await run_in_threadpool(list, query)
        
        if not docs:
            return None
        
        doc = docs[0]
        user_data = doc.to_dict()
        user_data["id"] = doc.id
        return user_data
    
    async def verify_user_credentials(self, email: str, password: str) -> dict:
        """Verify user credentials and return user data."""
        user = await self.get_user_by_email(email)
        
        if not user:
            raise InvalidCredentialsError("Invalid email or password")
        
        if bcrypt.checkpw(password.encode('utf-8'), user.get("password_hash").encode('utf-8')):
            return user
        else:
            raise InvalidCredentialsError("Invalid email or password")
    
    async def get_user_by_id(self, user_id: str) -> dict | None:
        """Get user by ID."""
        doc = await run_in_threadpool(self.collection.document(user_id).get)
        
        if not doc.exists:
            return None
        
        user_data = doc.to_dict()
        user_data["id"] = doc.id
        return user_data


def get_user_service(db: Client = Depends(get_db)) -> UserService:
    return UserService(db)

