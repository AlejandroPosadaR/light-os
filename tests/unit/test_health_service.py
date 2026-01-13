"""
Unit tests for HealthService.
Tests business logic in isolation without database.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from app.services.health_service import (
    HealthService,
    InvalidDateError,
    HealthDataNotFoundError
)
from app.models.health import HealthDataCreate, HealthDataResponse, PaginatedHealthDataResponse


class TestParseDdMmYyyyDate:
    """Tests for date parsing functionality."""
    
    def test_valid_date(self):
        """Test parsing a valid DD-MM-YYYY date."""
        result = HealthService.parse_dd_mm_yyyy_date("08-01-2026")
        assert result == datetime(2026, 1, 8, tzinfo=timezone.utc)
    
    def test_valid_date_end_of_month(self):
        """Test parsing valid end of month date."""
        result = HealthService.parse_dd_mm_yyyy_date("31-12-2025")
        assert result == datetime(2025, 12, 31, tzinfo=timezone.utc)
    
    def test_invalid_format_iso(self):
        """Test that ISO format is rejected."""
        with pytest.raises(InvalidDateError) as exc:
            HealthService.parse_dd_mm_yyyy_date("2026-01-08")
        assert "Invalid date format" in str(exc.value)
    
    def test_invalid_format_slash(self):
        """Test that slash format is rejected."""
        with pytest.raises(InvalidDateError):
            HealthService.parse_dd_mm_yyyy_date("08/01/2026")
    
    def test_invalid_date_february_31(self):
        """Test that invalid date Feb 31 is rejected."""
        with pytest.raises(InvalidDateError):
            HealthService.parse_dd_mm_yyyy_date("31-02-2026")
    
    def test_invalid_month_13(self):
        """Test that month > 12 is rejected."""
        with pytest.raises(InvalidDateError) as exc:
            HealthService.parse_dd_mm_yyyy_date("08-13-2026")
        assert "Month must be between" in str(exc.value)
    
    def test_invalid_day_32(self):
        """Test that day > 31 is rejected."""
        with pytest.raises(InvalidDateError) as exc:
            HealthService.parse_dd_mm_yyyy_date("32-01-2026")
        assert "Day must be between" in str(exc.value)
    
    def test_invalid_year_too_old(self):
        """Test that year before 1900 is rejected."""
        with pytest.raises(InvalidDateError):
            HealthService.parse_dd_mm_yyyy_date("08-01-1800")
    
    def test_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(InvalidDateError):
            HealthService.parse_dd_mm_yyyy_date("")


class TestHealthServiceInit:
    """Tests for HealthService initialization."""
    
    def test_initialization(self, mock_db):
        """Test service initializes correctly."""
        service = HealthService(mock_db)
        assert service.db == mock_db
        mock_db.collection.assert_called_once_with("health_data")


class TestCreateHealthData:
    """Tests for creating health data."""
    
    @pytest.fixture
    def health_service(self, mock_db):
        """Create HealthService with mocked database."""
        return HealthService(mock_db)
    
    @pytest.fixture
    def valid_health_data(self):
        """Valid health data for testing."""
        return HealthDataCreate(
            timestamp=datetime(2026, 1, 8, 8, 30, tzinfo=timezone.utc),
            steps=5000,
            calories=300,
            sleep_hours=7.5
        )
    
    @pytest.mark.asyncio
    async def test_create_health_data_success(self, health_service, valid_health_data, mock_db):
        """Test successful health data creation."""
        # Setup mock
        mock_doc = Mock()
        mock_db.collection.return_value.document.return_value = mock_doc
        
        result = await health_service.create_health_data("user123", valid_health_data)
        
        assert result.user_id == "user123"
        assert result.steps == 5000
        assert result.calories == 300
        assert result.sleep_hours == 7.5
        assert result.id is not None
        assert result.created_at is not None
        assert result.created_at.tzinfo == timezone.utc
        mock_doc.set.assert_called_once()


class TestGetHealthDataSummary:
    """Tests for health data summary calculation."""
    
    @pytest.fixture
    def health_service(self, mock_db):
        """Create HealthService with mocked database."""
        return HealthService(mock_db)
    
    @pytest.mark.asyncio
    async def test_summary_calculation(self, health_service):
        """Test summary calculates correct totals and averages."""
        # Mock entries
        now = datetime.now(timezone.utc)
        mock_entries = [
            HealthDataResponse(
                id="1", user_id="user123",
                timestamp=now,
                steps=5000, calories=300, sleep_hours=7,
                created_at=now
            ),
            HealthDataResponse(
                id="2", user_id="user123",
                timestamp=now,
                steps=7000, calories=400, sleep_hours=8,
                created_at=now
            ),
        ]
        
        # Patch get_health_data to return PaginatedHealthDataResponse
        mock_response = PaginatedHealthDataResponse(
            data=mock_entries,
            next_cursor=None,
            has_more=False,
            limit=10000
        )
        with patch.object(health_service, 'get_health_data', return_value=mock_response):
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            end = datetime(2026, 1, 31, tzinfo=timezone.utc)
            
            result = await health_service.get_health_data_summary("user123", start, end)
            
            assert result.total_steps == 12000  # 5000 + 7000
            assert result.average_sleep_hours == 7.5  # (7 + 8) / 2
            assert result.average_calories == 350.0  # (300 + 400) / 2
    
    @pytest.mark.asyncio
    async def test_summary_no_data_raises_error(self, health_service):
        """Test that summary raises error when no data found."""
        empty_response = PaginatedHealthDataResponse(
            data=[],
            next_cursor=None,
            has_more=False,
            limit=10000
        )
        with patch.object(health_service, 'get_health_data', return_value=empty_response):
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            end = datetime(2026, 1, 31, tzinfo=timezone.utc)
            
            with pytest.raises(HealthDataNotFoundError):
                await health_service.get_health_data_summary("user123", start, end)


class TestPagination:
    """Tests for pagination functionality."""
    
    def test_encode_cursor(self):
        """Test cursor encoding."""
        timestamp = datetime(2026, 1, 8, 8, 30, 0, tzinfo=timezone.utc)
        doc_id = "test-doc-123"
        
        cursor = HealthService.encode_cursor(timestamp, doc_id)
        
        assert cursor is not None
        assert isinstance(cursor, str)
        assert len(cursor) > 0
    
    def test_decode_cursor(self):
        """Test cursor decoding."""
        timestamp = datetime(2026, 1, 8, 8, 30, 0, tzinfo=timezone.utc)
        doc_id = "test-doc-123"
        
        cursor = HealthService.encode_cursor(timestamp, doc_id)
        decoded_timestamp, decoded_doc_id = HealthService.decode_cursor(cursor)
        
        assert decoded_timestamp == timestamp
        assert decoded_doc_id == doc_id
    
    def test_decode_cursor_roundtrip(self):
        """Test cursor encode/decode roundtrip preserves timezone."""
        timestamp = datetime(2026, 1, 8, 8, 30, 0, tzinfo=timezone.utc)
        doc_id = "test-doc-456"
        
        cursor = HealthService.encode_cursor(timestamp, doc_id)
        decoded_timestamp, decoded_doc_id = HealthService.decode_cursor(cursor)
        
        assert decoded_timestamp.tzinfo == timezone.utc
        assert decoded_timestamp == timestamp
        assert decoded_doc_id == doc_id
    
    def test_decode_invalid_cursor(self):
        """Test decoding invalid cursor raises ValueError."""
        with pytest.raises(ValueError):
            HealthService.decode_cursor("invalid-cursor")
        
        with pytest.raises(ValueError):
            HealthService.decode_cursor("not-base64")
        
        with pytest.raises(ValueError):
            # Valid base64 but invalid JSON
            import base64
            invalid_json = base64.b64encode(b"not json").decode()
            HealthService.decode_cursor(invalid_json)
    
    def test_cursor_with_different_timestamps(self):
        """Test cursor encoding/decoding with various timestamp formats."""
        # Test with different timezone-aware timestamps
        timestamps = [
            datetime(2026, 1, 8, 8, 30, 0, tzinfo=timezone.utc),
            datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        ]
        
        for timestamp in timestamps:
            doc_id = f"doc-{timestamp.isoformat()}"
            cursor = HealthService.encode_cursor(timestamp, doc_id)
            decoded_timestamp, decoded_doc_id = HealthService.decode_cursor(cursor)
            
            assert decoded_timestamp == timestamp
            assert decoded_timestamp.tzinfo == timezone.utc
            assert decoded_doc_id == doc_id
    
    def test_cursor_handles_special_characters_in_doc_id(self):
        """Test cursor works with special characters in document ID."""
        timestamp = datetime(2026, 1, 8, 8, 30, 0, tzinfo=timezone.utc)
        special_doc_ids = [
            "doc-123",
            "doc_with_underscores",
            "doc.with.dots",
            "doc/with/slashes",
            "doc-with-dashes-123",
        ]
        
        for doc_id in special_doc_ids:
            cursor = HealthService.encode_cursor(timestamp, doc_id)
            decoded_timestamp, decoded_doc_id = HealthService.decode_cursor(cursor)
            
            assert decoded_doc_id == doc_id
            assert decoded_timestamp == timestamp
    
    @pytest.mark.asyncio
    async def test_get_health_data_pagination_with_mock(self, mock_db):
        """Test pagination logic using mocked Firestore queries (no real DB objects)."""
        from google.cloud.firestore_v1.base_query import FieldFilter
        
        # Create health service with mocked DB
        health_service = HealthService(mock_db)
        
        # Create mock documents that simulate Firestore query results
        def create_mock_doc(doc_id: str, timestamp: datetime, steps: int, calories: int, sleep_hours: float):
            """Helper to create a mock Firestore document."""
            mock_doc = Mock()
            mock_doc.id = doc_id
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                "user_id": "user123",
                "timestamp": timestamp,
                "steps": steps,
                "calories": calories,
                "sleepHours": sleep_hours,
                "created_at": timestamp
            }
            return mock_doc
        
        # Simulate 55 documents (more than limit of 50)
        from datetime import timedelta
        base_time = datetime(2024, 1, 8, 8, 0, 0, tzinfo=timezone.utc)
        mock_docs = [
            create_mock_doc(f"doc_{i:03d}", base_time + timedelta(hours=i), 1000+i, 200+i, 7.5)
            for i in range(55)
        ]
        
        # Mock the query chain - need separate query objects for first and second page
        # The service calls: collection.where().where().order_by().order_by().limit().stream()
        mock_query1 = Mock()
        mock_query1.where.return_value = mock_query1
        mock_query1.order_by.return_value = mock_query1
        mock_query1.limit.return_value = mock_query1
        mock_query1.stream.return_value = iter(mock_docs[:51])  # First page: 51 docs
        
        mock_query2 = Mock()
        mock_query2.where.return_value = mock_query2
        mock_query2.order_by.return_value = mock_query2
        mock_query2.limit.return_value = mock_query2
        mock_query2.start_after.return_value = mock_query2
        mock_query2.stream.return_value = iter(mock_docs[51:])  # Second page: 4 docs
        
        # Track calls to determine which query to return
        query_call_count = [0]
        def mock_where(*args, **kwargs):
            query_call_count[0] += 1
            if query_call_count[0] == 1:
                return mock_query1
            else:
                return mock_query2
        
        # Mock collection - it needs where() method that returns query
        mock_collection = Mock()
        mock_collection.where.side_effect = mock_where
        mock_collection.document.return_value.get.return_value = Mock(exists=True)
        mock_db.collection.return_value = mock_collection
        
        # Also need to set collection on health_service
        health_service.collection = mock_collection
        
        # Test first page
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = await health_service.get_health_data(
            "user123", start_date, end_date, cursor=None, limit=50
        )
        
        # Verify first page
        assert len(result.data) == 50
        assert result.has_more is True
        assert result.next_cursor is not None
        
        # Verify query was called correctly
        mock_query1.limit.assert_called_with(51)  # limit + 1
        
        # Test second page with cursor
        # Mock cursor document lookup - use the last doc from first page
        cursor_timestamp, cursor_doc_id = health_service.decode_cursor(result.next_cursor)
        mock_cursor_doc = create_mock_doc(
            cursor_doc_id, cursor_timestamp, 1000, 200, 7.5
        )
        mock_collection.document.return_value.get.return_value = mock_cursor_doc
        
        result2 = await health_service.get_health_data(
            "user123", start_date, end_date, cursor=result.next_cursor, limit=50
        )
        
        # Verify second page
        assert len(result2.data) == 4  # Remaining docs
        assert result2.has_more is False
        assert result2.next_cursor is None
        
        # Verify no overlap between pages
        first_page_ids = {entry.id for entry in result.data}
        second_page_ids = {entry.id for entry in result2.data}
        assert len(first_page_ids.intersection(second_page_ids)) == 0
    
    @pytest.mark.asyncio
    async def test_get_health_data_pagination_exact_limit(self, mock_db):
        """Test pagination when results exactly match limit."""
        from google.cloud.firestore_v1.base_query import FieldFilter
        
        # Create health service with mocked DB
        health_service = HealthService(mock_db)
        
        def create_mock_doc(doc_id: str, timestamp: datetime):
            mock_doc = Mock()
            mock_doc.id = doc_id
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                "user_id": "user123",
                "timestamp": timestamp,
                "steps": 1000,
                "calories": 200,
                "sleepHours": 7.5,
                "created_at": timestamp
            }
            return mock_doc
        
        # Exactly 25 documents
        from datetime import timedelta
        base_time = datetime(2024, 1, 8, 8, 0, 0, tzinfo=timezone.utc)
        mock_docs = [
            create_mock_doc(f"doc_{i:03d}", base_time + timedelta(hours=i))
            for i in range(25)
        ]
        
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = iter(mock_docs)  # Exactly 25, no extra
        
        # Mock collection
        mock_collection = Mock()
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        health_service.collection = mock_collection
        
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = await health_service.get_health_data(
            "user123", start_date, end_date, cursor=None, limit=25
        )
        
        # Should return all 25, no more pages
        assert len(result.data) == 25
        assert result.has_more is False
        assert result.next_cursor is None
