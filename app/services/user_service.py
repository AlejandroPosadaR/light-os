"""
User service for user management and authentication.
Handles user registration, login, and user data operations.
"""
# Standard library imports
import uuid
from datetime import datetime, timezone
from typing import Optional

# Third-party imports
import bcrypt
from fastapi import Depends
from google.cloud.firestore import Client
from google.cloud.firestore_v1.base_query import FieldFilter

# Local imports
from app.database import get_db
from app.models.user import CreateUser, User

class UserNotFoundError(Exception):
    """Raised when a user is not found."""
    pass


class UserAlreadyExistsError(Exception):
    """Raised when trying to create a user that already exists."""
    pass


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""
    pass


class UserService:
    """Service for user-related operations."""
    
    COLLECTION_NAME = "users"
    
    def __init__(self, db: Client):
        """
        Initialize user service.
        
        Args:
            db: Firestore client (injected via dependency)
        """
        self.db = db
        self.collection = self.db.collection(self.COLLECTION_NAME)
    
    async def create_user(self, user_data: CreateUser) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user (without password)
            
        Raises:
            UserAlreadyExistsError: If email already exists
        """
        # Check if email already exists
        email_query = self.collection.where(filter=FieldFilter("email", "==", user_data.email)).limit(1).stream()
        if list(email_query):
            raise UserAlreadyExistsError(f"Email {user_data.email} already registered")
        
        # Create user document
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
        password_hash = password_hash.decode('utf-8')
        user_doc = {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "password_hash": password_hash,
            "created_at": now,
        }
        
        # Store in Firestore
        self.collection.document(user_id).set(user_doc)
        
        # Return user without password
        return User(
            id=uuid.UUID(user_id),
            name=user_data.name,
            email=user_data.email,
            created_at=now,
            password=""  # Excluded from response
        )
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """
        Get user by email.
        
        Args:
            email: User email address
            
        Returns:
            User document as dict, or None if not found
        """
        query = self.collection.where(filter=FieldFilter("email", "==", email)).limit(1).stream()
        docs = list(query)
        
        if not docs:
            return None
        
        doc = docs[0]
        user_data = doc.to_dict()
        user_data["id"] = doc.id
        return user_data
    
    async def verify_user_credentials(self, email: str, password: str) -> dict:
        """
        Verify user credentials and return user data.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            User document as dict
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        user = await self.get_user_by_email(email)
        
        if not user:
            raise InvalidCredentialsError("Invalid email or password")
        
        if bcrypt.checkpw(password.encode('utf-8'), user.get("password_hash").encode('utf-8')):
            return user
        else:
            raise InvalidCredentialsError("Invalid email or password")
        
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User document as dict, or None if not found
        """
        doc = self.collection.document(user_id).get()
        
        if not doc.exists:
            return None
        
        user_data = doc.to_dict()
        user_data["id"] = doc.id
        return user_data

def get_user_service(db: Client = Depends(get_db)) -> UserService:
    """
    Dependency function to get user service instance.
    Used with FastAPI's Depends(get_user_service) to inject database.
    
    Args:
        db: Firestore client (injected via FastAPI Depends(get_db))
        
    Returns:
        UserService instance
    """
    return UserService(db)

