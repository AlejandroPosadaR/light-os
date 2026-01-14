"""
Unit tests for UserService.
Tests business logic in isolation without database.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from app.services.user_service import (
    UserService,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserNotFoundError
)
from app.models.user import CreateUser


class TestUserServiceInit:
    """Tests for UserService initialization."""
    
    def test_initialization(self, mock_db):
        """Test service initializes correctly."""
        service = UserService(mock_db)
        assert service.db == mock_db
        mock_db.collection.assert_called_once_with("users")


class TestCreateUser:
    """Tests for user creation."""
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create UserService with mocked database."""
        return UserService(mock_db)
    
    @pytest.fixture
    def valid_user_data(self):
        """Valid user data for testing."""
        return CreateUser(
            name="Test User",
            email="test@example.com",
            password="securepassword123"
        )
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, valid_user_data, mock_db):
        """Test successful user creation."""
        # Mock: no existing user with this email
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        mock_doc = Mock()
        mock_db.collection.return_value.document.return_value = mock_doc
        
        result = await user_service.create_user(valid_user_data)
        
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        assert result.id is not None
        mock_doc.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service, valid_user_data, mock_db):
        """Test creating user with existing email raises error."""
        # Mock: existing user with this email
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [Mock()]
        
        with pytest.raises(UserAlreadyExistsError) as exc:
            await user_service.create_user(valid_user_data)
        
        assert "already registered" in str(exc.value)


class TestVerifyCredentials:
    """Tests for credential verification."""
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create UserService with mocked database."""
        return UserService(mock_db)
    
    @pytest.mark.asyncio
    async def test_verify_valid_credentials(self, user_service):
        """Test verifying valid credentials returns user."""
        import bcrypt
        password = "correctpassword"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        mock_user = {
            "id": "user123",
            "email": "test@example.com",
            "password_hash": password_hash
        }
        
        with patch.object(user_service, 'get_user_by_email', return_value=mock_user):
            result = await user_service.verify_user_credentials(
                "test@example.com",
                password
            )
            
            assert result["id"] == "user123"
            assert result["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_verify_user_not_found(self, user_service):
        """Test verifying credentials for non-existent user."""
        with patch.object(user_service, 'get_user_by_email', return_value=None):
            with pytest.raises(InvalidCredentialsError):
                await user_service.verify_user_credentials(
                    "nonexistent@example.com",
                    "password"
                )
    
    @pytest.mark.asyncio
    async def test_verify_wrong_password(self, user_service):
        """Test verifying credentials with wrong password."""
        import bcrypt
        correct_password = "correctpassword"
        password_hash = bcrypt.hashpw(correct_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        mock_user = {
            "id": "user123",
            "email": "test@example.com",
            "password_hash": password_hash
        }
        
        with patch.object(user_service, 'get_user_by_email', return_value=mock_user):
            with pytest.raises(InvalidCredentialsError):
                await user_service.verify_user_credentials(
                    "test@example.com",
                    "wrongpassword"
                )


class TestGetUserByEmail:
    """Tests for getting user by email."""
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create UserService with mocked database."""
        return UserService(mock_db)
    
    @pytest.mark.asyncio
    async def test_get_user_found(self, user_service, mock_db):
        """Test getting existing user by email."""
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {"email": "test@example.com", "name": "Test"}
        mock_doc.id = "user123"
        
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        result = await user_service.get_user_by_email("test@example.com")
        
        assert result["email"] == "test@example.com"
        assert result["id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_service, mock_db):
        """Test getting non-existent user by email."""
        mock_db.collection.return_value.where.return_value.limit.return_value.stream.return_value = []
        
        result = await user_service.get_user_by_email("nonexistent@example.com")
        
        assert result is None


class TestGetUserById:
    """Tests for getting user by ID."""
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create UserService with mocked database."""
        return UserService(mock_db)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, user_service, mock_db):
        """Test getting existing user by ID."""
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"email": "test@example.com", "name": "Test"}
        mock_doc.id = "user123"
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = await user_service.get_user_by_id("user123")
        
        assert result["email"] == "test@example.com"
        assert result["id"] == "user123"
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service, mock_db):
        """Test getting non-existent user by ID."""
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = await user_service.get_user_by_id("nonexistent-id")
        
        assert result is None
