"""
Integration test fixtures.
These fixtures set up the Firestore emulator and FastAPI test client.
"""
import pytest
import os
from fastapi.testclient import TestClient
from google.cloud import firestore
from google.auth.credentials import AnonymousCredentials
from app.main import app
from app.dependencies import create_access_token


@pytest.fixture(scope="session")
def firestore_emulator_host():
    """Get Firestore emulator host from environment or use default."""
    return os.getenv("FIRESTORE_EMULATOR_HOST", "localhost:8080")


@pytest.fixture(scope="session")
def test_project_id():
    """Get test project ID."""
    return os.getenv("TEST_GCP_PROJECT_ID", "test-project")


@pytest.fixture(scope="function")
def test_db(firestore_emulator_host, test_project_id):
    """
    Create a test Firestore client connected to the emulator.
    Cleans up test data after each test.
    """
    os.environ["FIRESTORE_EMULATOR_HOST"] = firestore_emulator_host
    os.environ["GCP_PROJECT_ID"] = test_project_id
    
    test_client = firestore.Client(
        project=test_project_id,
        credentials=AnonymousCredentials()
    )
    
    # Clean before test
    for collection in test_client.collections():
        for doc in collection.stream():
            doc.reference.delete()
    
    yield test_client
    
    # Clean after test
    for collection in test_client.collections():
        for doc in collection.stream():
            doc.reference.delete()


@pytest.fixture
def client(test_db):
    """FastAPI test client with test database."""
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """Register a user and return user data with token."""
    user_data = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "testpassword123"
    }
    response = client.post("/auth/register", json=user_data)
    token_data = response.json()
    
    # Decode token to get user_id
    from jose import jwt
    from app.dependencies import SECRET_KEY, ALGORITHM
    decoded = jwt.decode(token_data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    
    return {
        "user_id": decoded["sub"],
        "email": user_data["email"],
        "password": user_data["password"],
        "access_token": token_data["access_token"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"}
    }


@pytest.fixture
def auth_headers(registered_user):
    """Just the auth headers for authenticated requests."""
    return registered_user["headers"]
