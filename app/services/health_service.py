import base64
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.encoders import jsonable_encoder
from google.cloud.firestore import Client, DocumentSnapshot
from google.cloud.firestore_v1.base_query import FieldFilter

from app.cache import bump_user_version, get, get_user_version, set
from app.database import get_db
from app.models.health import (
    HealthDataCreate,
    HealthDataResponse,
    HealthDataSummary,
    PaginatedHealthDataResponse,
)


class HealthDataNotFoundError(Exception):
    pass


class InvalidDateError(Exception):
    pass


class HealthService:
    """Service for health data operations."""
    
    COLLECTION_NAME = "health_data"
    
    def __init__(self, db: Client):
        self.db = db
        self.collection = self.db.collection(self.COLLECTION_NAME)
    
    @staticmethod
    def parse_dd_mm_yyyy_date(date_str: str) -> datetime:
        """Parse date string in DD-MM-YYYY format to UTC datetime."""
        pattern = r'^\d{2}-\d{2}-\d{4}$'
        if not re.match(pattern, date_str):
            raise InvalidDateError(f"Invalid date format. Expected DD-MM-YYYY, got '{date_str}'")
        
        try:
            day, month, year = date_str.split('-')
            day, month, year = int(day), int(month), int(year)
            
            if not (1 <= month <= 12):
                raise ValueError(f"Month must be between 01 and 12, got {month:02d}")
            if not (1 <= day <= 31):
                raise ValueError(f"Day must be between 01 and 31, got {day:02d}")
            if not (1900 <= year <= 2100):
                raise ValueError(f"Year must be between 1900 and 2100, got {year}")
            
            dt = datetime(year, month, day, tzinfo=timezone.utc)
            
            if dt.day != day or dt.month != month or dt.year != year:
                raise ValueError(f"Invalid date: {day:02d}-{month:02d}-{year}")
            
            return dt
        except ValueError as e:
            raise InvalidDateError(f"Invalid date: {str(e)}. Expected DD-MM-YYYY format")
        except Exception as e:
            raise InvalidDateError(f"Error parsing date '{date_str}': {str(e)}")
    
    async def create_health_data(self, user_id: str, health_data: HealthDataCreate) -> HealthDataResponse:
        """Create a new health data entry and invalidate cache."""
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        entry_doc = {
            "user_id": user_id,
            "timestamp": health_data.timestamp,
            "steps": health_data.steps,
            "calories": health_data.calories,
            "sleepHours": health_data.sleep_hours,
            "created_at": now
        }
        
        self.collection.document(entry_id).set(entry_doc)
        bump_user_version(user_id)
        
        return HealthDataResponse(
            id=entry_id,
            user_id=user_id,
            timestamp=health_data.timestamp,
            steps=health_data.steps,
            calories=health_data.calories,
            sleep_hours=health_data.sleep_hours,
            created_at=now
        )
    
    @staticmethod
    def encode_cursor(timestamp: datetime, doc_id: str) -> str:
        """Encode pagination cursor from timestamp and document ID."""
        cursor_data = {"timestamp": timestamp.isoformat(), "id": doc_id}
        return base64.b64encode(json.dumps(cursor_data).encode()).decode()
    
    @staticmethod
    def decode_cursor(cursor: str) -> tuple[datetime, str]:
        """Decode pagination cursor to timestamp and document ID."""
        try:
            cursor_data = json.loads(base64.b64decode(cursor.encode()).decode())
            timestamp = datetime.fromisoformat(cursor_data["timestamp"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp, cursor_data["id"]
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid cursor format: {str(e)}")
    
    def _build_cache_key(self, user_id: str, start_date: datetime | None, end_date: datetime | None, cursor: str | None, limit: int, version: int) -> str:
        query_str = f"{start_date.isoformat() if start_date else ''}:{end_date.isoformat() if end_date else ''}:{cursor or ''}:{limit}"
        query_hash = hashlib.md5(query_str.encode()).hexdigest()[:8]
        return f"health:{user_id}:range:v{version}:{query_hash}"
    
    async def get_health_data(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        cursor: str | None = None,
        limit: int = 50
    ) -> PaginatedHealthDataResponse:
        """Get health data entries with pagination and caching."""
        version = get_user_version(user_id)
        cache_key = self._build_cache_key(user_id, start_date, end_date, cursor, limit, version)
        cached_data = get(cache_key)
        
        if cached_data:
            cached_dict = json.loads(cached_data.decode())
            return PaginatedHealthDataResponse(**cached_dict)
        
        if limit < 1 or limit > 100:
            limit = 50
        
        query = self.collection.where(filter=FieldFilter("user_id", "==", user_id))
        
        if start_date:
            query = query.where(filter=FieldFilter("timestamp", ">=", start_date))
        if end_date:
            end_of_day = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(filter=FieldFilter("timestamp", "<=", end_of_day))
        
        query = query.order_by("timestamp").order_by("__name__")
        
        if cursor:
            try:
                cursor_timestamp, cursor_doc_id = self.decode_cursor(cursor)
                cursor_doc_ref = self.collection.document(cursor_doc_id)
                cursor_doc = cursor_doc_ref.get()
                if cursor_doc.exists:
                    query = query.start_after(cursor_doc)
            except (ValueError, Exception):
                pass
        
        query = query.limit(limit + 1)
        docs = list(query.stream())
        
        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]
        
        entries = []
        last_doc: DocumentSnapshot | None = None
        
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            
            if "timestamp" in data and isinstance(data["timestamp"], datetime):
                if data["timestamp"].tzinfo is None:
                    data["timestamp"] = data["timestamp"].replace(tzinfo=timezone.utc)
            
            if "created_at" in data and isinstance(data["created_at"], datetime):
                if data["created_at"].tzinfo is None:
                    data["created_at"] = data["created_at"].replace(tzinfo=timezone.utc)
            
            entries.append(HealthDataResponse(**data))
            last_doc = doc
        
        next_cursor = None
        if has_more and last_doc:
            last_timestamp = last_doc.to_dict().get("timestamp")
            if isinstance(last_timestamp, datetime):
                if last_timestamp.tzinfo is None:
                    last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
                next_cursor = self.encode_cursor(last_timestamp, last_doc.id)
        
        response = PaginatedHealthDataResponse(
            data=entries,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit
        )
        
        cache_data = jsonable_encoder(response)
        set(cache_key, json.dumps(cache_data).encode(), ex=300)
        
        return response
    
    async def get_health_data_summary(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> HealthDataSummary:
        """Get summary statistics for health data within a date range."""
        result = await self.get_health_data(user_id, start_date, end_date, limit=10000)
        entries = result.data
        
        if not entries:
            raise HealthDataNotFoundError("User has no health data entries")
        
        total_steps = sum(entry.steps for entry in entries)
        total_calories = sum(entry.calories for entry in entries)
        total_sleep_hours = sum(entry.sleep_hours for entry in entries)
        
        num_entries = len(entries)
        average_calories = float(total_calories / num_entries) if num_entries > 0 else 0.0
        average_sleep_hours = float(total_sleep_hours / num_entries) if num_entries > 0 else 0.0
        
        return HealthDataSummary(
            total_steps=total_steps,
            average_calories=average_calories,
            average_sleep_hours=average_sleep_hours
        )


def get_health_service(db: Client = Depends(get_db)) -> HealthService:
    return HealthService(db)

