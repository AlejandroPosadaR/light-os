from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


class HealthDataCreate(BaseModel):
    timestamp: datetime = Field(..., examples=["2026-01-08T08:30:00Z"])
    steps: int = Field(..., ge=0, le=100000)
    calories: int = Field(..., ge=0, le=30000)
    sleep_hours: float = Field(..., ge=0.0, le=24.0, alias="sleepHours")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        now_utc = datetime.now(timezone.utc)
        
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)
        
        if v > now_utc:
            raise ValueError("Timestamp cannot be in the future")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-01-08T08:30:00Z",
                "steps": 1200,
                "calories": 450,
                "sleepHours": 7.5
            }
        },
        "populate_by_name": True
    }


class HealthDataResponse(BaseModel):
    id: str
    user_id: str
    timestamp: datetime
    steps: int
    calories: int
    sleep_hours: float = Field(..., alias="sleepHours")
    created_at: datetime
    
    model_config = {
        "populate_by_name": True,  # Allow both snake_case and camelCase
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
    total_steps: int
    average_calories: float
    average_sleep_hours: float = Field(..., alias="averageSleepHours")
    
    model_config = {
        "populate_by_name": True,  # Allow both snake_case and camelCase
        "json_schema_extra": {
            "example": {
                "total_steps": 15000,
                "average_calories": 450.0,
                "averageSleepHours": 7.5
            }
        }
    }


class PaginatedHealthDataResponse(BaseModel):
    data: list[HealthDataResponse]
    next_cursor: str | None = None
    has_more: bool
    limit: int
    
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