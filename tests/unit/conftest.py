"""
Unit test fixtures - no external dependencies needed.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone


@pytest.fixture
def mock_db():
    """Mock Firestore client for unit tests."""
    db = Mock()
    db.collection = Mock(return_value=Mock())
    return db


@pytest.fixture
def mock_collection():
    """Mock Firestore collection."""
    return Mock()
