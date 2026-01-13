"""
Health data service for health tracking operations.
Handles health data CRUD, filtering, and summary calculations.
"""
from typing import List, Optional, Tuple
from datetime import datetime, timezone
import uuid
import re
import base64
import json
from fastapi import Depends
from google.cloud.firestore import Client, DocumentSnapshot
from app.database import get_db
from app.models.health import HealthDataCreate, HealthDataResponse, HealthDataSummary


class HealthDataNotFoundError(Exception):
    """Raised when health data is not found."""
    pass


class InvalidDateError(Exception):
    """Raised when date format is invalid."""
    pass


class HealthService:
    """Service for health data operations."""
    
    COLLECTION_NAME = "health_data"
    
    def __init__(self, db: Client):
        """
        Initialize health service.
        
        Args:
            db: Firestore client (injected via dependency)
        """
        self.db = db
        self.collection = self.db.collection(self.COLLECTION_NAME)
    
    @staticmethod
    def parse_dd_mm_yyyy_date(date_str: str) -> datetime:
        """
        Parse a date string in DD-MM-YYYY format and return a datetime object at midnight UTC.
        
        Args:
            date_str: Date string in DD-MM-YYYY format (e.g., "08-01-2026")
            
        Returns:
            datetime object at midnight UTC
            
        Raises:
            InvalidDateError: If date format is invalid
        """
        # Validate format: DD-MM-YYYY
        pattern = r'^\d{2}-\d{2}-\d{4}$'
        if not re.match(pattern, date_str):
            raise InvalidDateError(
                f"Invalid date format. Expected DD-MM-YYYY (e.g., '08-01-2026'), got '{date_str}'"
            )
        
        try:
            day, month, year = date_str.split('-')
            day, month, year = int(day), int(month), int(year)
            
            # Validate date values
            if not (1 <= month <= 12):
                raise ValueError(f"Month must be between 01 and 12, got {month:02d}")
            if not (1 <= day <= 31):
                raise ValueError(f"Day must be between 01 and 31, got {day:02d}")
            if not (1900 <= year <= 2100):
                raise ValueError(f"Year must be between 1900 and 2100, got {year}")
            
            # Create datetime at midnight UTC
            dt = datetime(year, month, day, tzinfo=timezone.utc)
            
            # Validate that the date is actually valid (e.g., catches 31-02-2026)
            if dt.day != day or dt.month != month or dt.year != year:
                raise ValueError(f"Invalid date: {day:02d}-{month:02d}-{year}")
            
            return dt
        except ValueError as e:
            raise InvalidDateError(
                f"Invalid date: {str(e)}. Expected DD-MM-YYYY format (e.g., '08-01-2026')"
            )
        except Exception as e:
            raise InvalidDateError(
                f"Error parsing date '{date_str}': {str(e)}. Expected DD-MM-YYYY format (e.g., '08-01-2026')"
            )
    
    async def create_health_data(self, user_id: str, health_data: HealthDataCreate) -> HealthDataResponse:
        """
        Create a new health data entry.
        
        Args:
            user_id: User ID
            health_data: Health data to create
            
        Returns:
            Created health data entry
        """
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        entry_doc = {
            "user_id": user_id,
            "timestamp": health_data.timestamp,
            "steps": health_data.steps,
            "calories": health_data.calories,
            "sleepHours": health_data.sleepHours,
            "created_at": now
        }
        
        # Store in Firestore
        self.collection.document(entry_id).set(entry_doc)
        
        return HealthDataResponse(
            id=entry_id,
            user_id=user_id,
            timestamp=health_data.timestamp,
            steps=health_data.steps,
            calories=health_data.calories,
            sleepHours=health_data.sleepHours,
            created_at=now
        )
    
    @staticmethod
    def encode_cursor(timestamp: datetime, doc_id: str) -> str:
        """Encode cursor from timestamp and document ID."""
        cursor_data = {
            "timestamp": timestamp.isoformat(),
            "id": doc_id
        }
        return base64.b64encode(json.dumps(cursor_data).encode()).decode()
    
    @staticmethod
    def decode_cursor(cursor: str) -> Tuple[datetime, str]:
        """Decode cursor to timestamp and document ID."""
        try:
            cursor_data = json.loads(base64.b64decode(cursor.encode()).decode())
            timestamp = datetime.fromisoformat(cursor_data["timestamp"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            doc_id = cursor_data["id"]
            return timestamp, doc_id
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid cursor format: {str(e)}")
    
    async def get_health_data(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[List[HealthDataResponse], Optional[str], bool]:
        """
        Get health data entries for a user with pagination support.
        
        Args:
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            cursor: Optional cursor for pagination
            limit: Maximum number of results (default 50, max 100)
            
        Returns:
            Tuple of (entries, next_cursor, has_more)
        """
        # Validate limit
        if limit < 1 or limit > 100:
            limit = 50
        
        # Query Firestore for user's health data
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection.where(filter=FieldFilter("user_id", "==", user_id))
        
        # Apply date filters if provided
        if start_date:
            query = query.where(filter=FieldFilter("timestamp", ">=", start_date))
        if end_date:
            # Include entire end date (end of day)
            end_of_day = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(filter=FieldFilter("timestamp", "<=", end_of_day))
        
        # Order by timestamp, then by document ID for consistent pagination
        query = query.order_by("timestamp").order_by("__name__")
        
        # Apply cursor if provided
        # Note: With multiple order_by (timestamp + __name__), we need document snapshot
        # This is the standard Firestore approach for multi-field pagination
        if cursor:
            try:
                cursor_timestamp, cursor_doc_id = self.decode_cursor(cursor)
                # Get document reference (more efficient than full snapshot fetch)
                # Firestore's start_after() with multiple order_by requires the document
                cursor_doc_ref = self.collection.document(cursor_doc_id)
                cursor_doc = cursor_doc_ref.get()
                if cursor_doc.exists:
                    # Use start_after with document snapshot (required for multi-field ordering)
                    query = query.start_after(cursor_doc)
                else:
                    # Document doesn't exist, invalid cursor - start from beginning
                    pass
            except (ValueError, Exception):
                # Invalid cursor format or error, ignore it and start from beginning
                pass
        
        # Apply limit (fetch one extra to check if there's more)
        query = query.limit(limit + 1)
        
        # Execute query
        docs = list(query.stream())
        
        # Check if there are more results
        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]
        
        entries = []
        last_doc: Optional[DocumentSnapshot] = None
        
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            
            # Ensure timestamp is timezone-aware datetime
            if "timestamp" in data and isinstance(data["timestamp"], datetime):
                if data["timestamp"].tzinfo is None:
                    data["timestamp"] = data["timestamp"].replace(tzinfo=timezone.utc)
            
            # Ensure created_at is timezone-aware datetime
            if "created_at" in data and isinstance(data["created_at"], datetime):
                if data["created_at"].tzinfo is None:
                    data["created_at"] = data["created_at"].replace(tzinfo=timezone.utc)
            
            entries.append(HealthDataResponse(**data))
            last_doc = doc
        
        # Generate next cursor if there are more results
        next_cursor = None
        if has_more and last_doc:
            last_timestamp = last_doc.to_dict().get("timestamp")
            if isinstance(last_timestamp, datetime):
                if last_timestamp.tzinfo is None:
                    last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
                next_cursor = self.encode_cursor(last_timestamp, last_doc.id)
        
        return entries, next_cursor, has_more
    
    async def get_health_data_summary(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> HealthDataSummary:
        """
        Get summary statistics for health data within a date range.
        
        Args:
            user_id: User ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Health data summary
            
        Raises:
            HealthDataNotFoundError: If no data found for user
        """
        # Get entries in date range (no pagination for summary - get all)
        entries, _, _ = await self.get_health_data(user_id, start_date, end_date, limit=10000)
        
        if not entries:
            raise HealthDataNotFoundError("User has no health data entries")
        
        # Calculate statistics
        total_steps = sum(entry.steps for entry in entries)
        total_calories = sum(entry.calories for entry in entries)
        total_sleep_hours = sum(entry.sleepHours for entry in entries)
        
        num_entries = len(entries)
        average_calories = float(total_calories / num_entries) if num_entries > 0 else 0.0
        average_sleep_hours = float(total_sleep_hours / num_entries) if num_entries > 0 else 0.0
        
        return HealthDataSummary(
            total_steps=total_steps,
            average_calories=average_calories,
            averageSleepHours=average_sleep_hours
        )

def get_health_service(db: Client = Depends(get_db)) -> HealthService:
    """
    Dependency function to get health service instance.
    Used with FastAPI's Depends(get_health_service) to inject database.
    
    Args:
        db: Firestore client (injected via FastAPI Depends(get_db))
        
    Returns:
        HealthService instance
    """
    return HealthService(db)

