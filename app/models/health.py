"""
Health data models for the health tracking API.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, List


class HealthDataCreate(BaseModel):
    """Request model for creating health data."""
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp",
        examples=["2026-01-08T08:30:00Z"]
    )
    steps: int = Field(
        ...,
        ge=0,
        le=100000,  # Max reasonable steps per day
        description="Number of steps",
        examples=[1200]
    )
    calories: int = Field(
        ...,
        ge=0,
        le=30000,  # Max reasonable calories per day
        description="Calories burned",
        examples=[450]
    )
    sleepHours: float = Field(
        ...,
        ge=0.0,
        le=24.0,
        description="Hours of sleep",
        examples=[7.5]
    )
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """
        Ensure timestamp is not in the future.
        Handles both timezone-aware and timezone-naive datetimes.
        """
        # Get current time in UTC (timezone-aware)
        now_utc = datetime.now(timezone.utc)
        
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            # If input has timezone, convert to UTC for comparison
            v = v.astimezone(timezone.utc)
        
        if v > now_utc:
            raise ValueError('Timestamp cannot be in the future')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-01-08T08:30:00Z",
                "steps": 1200,
                "calories": 450,
                "sleepHours": 7.5
            }
        }
    }


class HealthDataResponse(BaseModel):
    """Response model for health data."""
    id: str
    user_id: str
    timestamp: datetime
    steps: int
    calories: int
    sleepHours: float
    created_at: datetime = Field(..., description="Health data entry creation timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "abc123",
                "user_id": "user123",
                "timestamp": "2026-01-08T08:30:00Z",
                "steps": 1200,
                "calories": 450,
                "sleepHours": 7.5,
                "created_at": "2026-01-08T08:30:00Z"
            }
        }
    }

class HealthDataSummary(BaseModel):
    """Summary model for health data."""
    total_steps: int
    average_calories: float
    averageSleepHours: float
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_steps": 15000,
                "average_calories": 450.0,
                "averageSleepHours": 7.5
            }
        }
    }


class PaginatedHealthDataResponse(BaseModel):
    """Paginated response model for health data."""
    data: List[HealthDataResponse]
    next_cursor: Optional[str] = Field(None, description="Cursor for next page (null if no more pages)")
    has_more: bool = Field(..., description="Whether there are more results available")
    limit: int = Field(..., description="Number of items per page")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "id": "abc123",
                        "user_id": "user123",
                        "timestamp": "2026-01-08T08:30:00Z",
                        "steps": 1200,
                        "calories": 450,
                        "sleepHours": 7.5,
                        "created_at": "2026-01-08T08:30:00Z"
                    }
                ],
                "next_cursor": "eyJ0aW1lc3RhbXAiOiIyMDI2LTAxLTA4VDA4OjMwOjAwWiIsImlkIjoiYWJjMTIzIn0=",
                "has_more": True,
                "limit": 50
            }
        }
    }