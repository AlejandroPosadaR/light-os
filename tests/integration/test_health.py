"""
Integration tests for health data endpoints.
Tests the full request/response cycle with database.
"""
import pytest
from datetime import datetime, timezone, timedelta


class TestCreateHealthData:
    """Tests for POST /users/{user_id}/health-data endpoint."""
    
    @pytest.fixture
    def valid_health_data(self):
        """Valid health data payload."""
        return {
            "timestamp": "2026-01-08T08:30:00Z",
            "steps": 5000,
            "calories": 300,
            "sleepHours": 7.5
        }
    
    def test_create_health_data_success(self, client, registered_user, valid_health_data):
        """Test successful health data creation."""
        user_id = registered_user["user_id"]
        
        response = client.post(
            f"/users/{user_id}/health-data",
            json=valid_health_data,
            headers=registered_user["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["steps"] == 5000
        assert data["calories"] == 300
        assert data["sleepHours"] == 7.5
        assert data["user_id"] == user_id
        assert "id" in data
        assert "created_at" in data
    
    def test_create_health_data_unauthorized(self, client, valid_health_data):
        """Test creating health data without authentication fails."""
        response = client.post(
            "/users/some-user-id/health-data",
            json=valid_health_data
        )
        
        assert response.status_code == 401  # 401 Unauthorized (no token) is correct
    
    def test_create_health_data_wrong_user(self, client, registered_user, valid_health_data):
        """Test creating health data for different user fails."""
        response = client.post(
            "/users/different-user-id/health-data",
            json=valid_health_data,
            headers=registered_user["headers"]
        )
        
        assert response.status_code == 403
        assert "only access your own data" in response.json()["detail"]
    
    def test_create_health_data_invalid_steps(self, client, registered_user):
        """Test creating health data with negative steps fails."""
        user_id = registered_user["user_id"]
        
        response = client.post(
            f"/users/{user_id}/health-data",
            json={
                "timestamp": "2026-01-08T08:30:00Z",
                "steps": -100,  # Invalid
                "calories": 300,
                "sleepHours": 7.5
            },
            headers=registered_user["headers"]
        )
        
        assert response.status_code == 422


class TestGetHealthData:
    """Tests for GET /users/{user_id}/health-data endpoint."""
    
    @pytest.fixture
    def user_with_health_data(self, client, registered_user):
        """Create user with some health data."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        # Create multiple health entries
        entries = [
            {"timestamp": "2026-01-08T08:00:00Z", "steps": 5000, "calories": 300, "sleepHours": 7},
            {"timestamp": "2026-01-09T08:00:00Z", "steps": 7000, "calories": 400, "sleepHours": 8},
            {"timestamp": "2026-01-10T08:00:00Z", "steps": 6000, "calories": 350, "sleepHours": 7.5},
        ]
        
        for entry in entries:
            client.post(f"/users/{user_id}/health-data", json=entry, headers=headers)
        
        return registered_user
    
    def test_get_health_data_success(self, client, user_with_health_data):
        """Test getting health data with pagination."""
        user_id = user_with_health_data["user_id"]
        headers = user_with_health_data["headers"]
        
        # start and end are required query parameters
        response = client.get(
            f"/users/{user_id}/health-data",
            params={"start": "08-01-2026", "end": "10-01-2026"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "next_cursor" in data
        assert "has_more" in data
        assert "limit" in data
        assert len(data["data"]) == 3
        assert data["limit"] == 50
    
    def test_get_health_data_with_date_filter(self, client, user_with_health_data):
        """Test getting health data with date filter."""
        user_id = user_with_health_data["user_id"]
        headers = user_with_health_data["headers"]
        
        response = client.get(
            f"/users/{user_id}/health-data",
            params={"start": "08-01-2026", "end": "09-01-2026"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2  # Only Jan 8 and Jan 9
    
    def test_get_health_data_empty(self, client, registered_user):
        """Test getting health data when none exists."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        # start and end are required query parameters
        response = client.get(
            f"/users/{user_id}/health-data",
            params={"start": "01-01-2026", "end": "31-01-2026"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["has_more"] is False
    
    def test_get_health_data_wrong_user(self, client, registered_user):
        """Test getting health data for different user fails."""
        response = client.get(
            "/users/different-user-id/health-data",
            headers=registered_user["headers"]
        )
        
        assert response.status_code == 403
    
    def test_get_health_data_invalid_date_format(self, client, registered_user):
        """Test getting health data with invalid date format."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        response = client.get(
            f"/users/{user_id}/health-data",
            params={"start": "2026-01-08", "end": "2026-01-10"},  # Wrong format (should be DD-MM-YYYY)
            headers=headers
        )
        
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]
    
    def test_get_health_data_start_after_end(self, client, registered_user):
        """Test getting health data with start date after end date fails."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        response = client.get(
            f"/users/{user_id}/health-data",
            params={"start": "31-01-2026", "end": "01-01-2026"},
            headers=headers
        )
        
        assert response.status_code == 400
        assert "start must be before" in response.json()["detail"]
    
    def test_get_health_data_pagination(self, client, registered_user):
        """Test pagination with cursor and limit."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        # Create more than 50 entries to test pagination
        from datetime import datetime, timezone, timedelta
        # Use dates in the past to avoid "future timestamp" validation error
        base_date = datetime(2024, 1, 8, 8, 0, 0, tzinfo=timezone.utc)
        
        for i in range(60):
            timestamp = base_date + timedelta(days=i % 10, hours=i % 24)
            entry = {
                "timestamp": timestamp.isoformat().replace('+00:00', 'Z'),
                "steps": 5000 + i,
                "calories": 300 + i,
                "sleepHours": 7.0
            }
            response = client.post(f"/users/{user_id}/health-data", json=entry, headers=headers)
            assert response.status_code == 201
        
        # First page with limit 25
        response = client.get(
            f"/users/{user_id}/health-data",
            params={"start": "08-01-2024", "end": "17-01-2024", "limit": 25},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 25
        assert data["limit"] == 25
        assert data["has_more"] is True
        assert data["next_cursor"] is not None
        
        # Second page using cursor
        next_cursor = data["next_cursor"]
        response = client.get(
            f"/users/{user_id}/health-data",
            params={"start": "08-01-2024", "end": "17-01-2024", "limit": 25, "cursor": next_cursor},
            headers=headers
        )
        
        assert response.status_code == 200
        data2 = response.json()
        assert len(data2["data"]) == 25
        assert data2["limit"] == 25
        
        # Verify no overlap between pages
        first_page_ids = {item["id"] for item in data["data"]}
        second_page_ids = {item["id"] for item in data2["data"]}
        assert len(first_page_ids.intersection(second_page_ids)) == 0


class TestGetHealthDataSummary:
    """Tests for GET /users/{user_id}/summary endpoint."""
    
    @pytest.fixture
    def user_with_health_data(self, client, registered_user):
        """Create user with some health data."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        entries = [
            {"timestamp": "2026-01-08T08:00:00Z", "steps": 5000, "calories": 300, "sleepHours": 7},
            {"timestamp": "2026-01-09T08:00:00Z", "steps": 7000, "calories": 400, "sleepHours": 8},
        ]
        
        for entry in entries:
            client.post(f"/users/{user_id}/health-data", json=entry, headers=headers)
        
        return registered_user
    
    def test_summary_success(self, client, user_with_health_data):
        """Test getting health data summary."""
        user_id = user_with_health_data["user_id"]
        headers = user_with_health_data["headers"]
        
        response = client.get(
            f"/users/{user_id}/summary",
            params={"start": "08-01-2026", "end": "09-01-2026"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_steps"] == 12000  # 5000 + 7000
        assert data["averageSleepHours"] == 7.5  # (7 + 8) / 2 - JSON uses camelCase
        assert data["average_calories"] == 350.0  # (300 + 400) / 2
    
    def test_summary_no_data(self, client, registered_user):
        """Test summary when no data exists."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        response = client.get(
            f"/users/{user_id}/summary",
            params={"start": "01-01-2026", "end": "31-01-2026"},
            headers=headers
        )
        
        assert response.status_code == 404
        assert "no health data" in response.json()["detail"]
    
    def test_summary_missing_dates(self, client, registered_user):
        """Test summary without required dates fails."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        response = client.get(
            f"/users/{user_id}/summary",
            headers=headers
        )
        
        assert response.status_code == 422  # Missing required params
    
    def test_summary_invalid_date_format(self, client, registered_user):
        """Test summary with invalid date format fails."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        response = client.get(
            f"/users/{user_id}/summary",
            params={"start": "2026-01-08", "end": "2026-01-10"},  # Wrong format (should be DD-MM-YYYY)
            headers=headers
        )
        
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]
    
    def test_summary_invalid_date_range(self, client, registered_user):
        """Test summary with start after end fails."""
        user_id = registered_user["user_id"]
        headers = registered_user["headers"]
        
        response = client.get(
            f"/users/{user_id}/summary",
            params={"start": "31-01-2026", "end": "01-01-2026"},
            headers=headers
        )
        
        assert response.status_code == 400
        assert "start must be before" in response.json()["detail"]


class TestHealthCheck:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "Health API" in response.json()["message"]
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
