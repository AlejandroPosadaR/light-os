"""
Health data endpoints with authentication and authorization.
Prevents cross-user data access by verifying user_id matches authenticated user.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.dependencies import get_current_user, verify_user_access
from app.database import get_db
from app.models.health import HealthDataCreate, HealthDataResponse, HealthDataSummary, PaginatedHealthDataResponse
from app.services.health_service import (
    get_health_service,
    HealthService,
    InvalidDateError,
    HealthDataNotFoundError
)
from typing import List, Optional

health_router = APIRouter(prefix="/users", tags=["health"])


@health_router.post(
    "/{user_id}/health-data",
    response_model=HealthDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit health data",
    description="""
    Submit health data for a user.
    
    **Security:**
    - Requires authentication (Bearer token)
    - User can only submit data for their own user_id
    - Cross-user access is prevented
    
    **Authorization:**
    The user_id in the URL path must match the authenticated user's ID from the JWT token.
    """
)
async def create_health_data(
    user_id: str,
    health_data: HealthDataCreate,
    verified_user_id: str = Depends(verify_user_access),
    health_service: HealthService = Depends(get_health_service)
):
    """
    Create health data entry.
    
    The verify_user_access dependency ensures:
    1. User is authenticated (has valid JWT token)
    2. user_id in path matches authenticated user's ID
    3. Returns 403 Forbidden if user tries to access another user's data
    """
    return await health_service.create_health_data(user_id, health_data)


@health_router.get(
    "/{user_id}/health-data",
    response_model=PaginatedHealthDataResponse,
    summary="Get user's health data",
    description="""
    Retrieve health data entries for a user within a date range with pagination.
    
    **Query Parameters:**
    - `start` (required): Start date in DD-MM-YYYY format (e.g., '08-01-2026')
    - `end` (required): End date in DD-MM-YYYY format (e.g., '10-01-2026')
    - `cursor` (optional): Cursor for pagination (from previous response's next_cursor)
    - `limit` (optional): Number of results per page (default: 50, max: 100)
    
    **Date Format:**
    - Only DD-MM-YYYY format is accepted (e.g., '08-01-2026' for January 8, 2026)
    - Dates are interpreted as midnight UTC
    
    **Pagination:**
    - Use `next_cursor` from response to get the next page
    - `has_more` indicates if there are more results
    - Default limit is 50 items per page
    
    **Security:**
    - Requires authentication
    - User can only retrieve their own health data
    - Cross-user access is prevented
    """
)
async def get_health_data(
    user_id: str,
    start: str = Query(
        ...,
        description="Start date in DD-MM-YYYY format (e.g., '08-01-2026')",
        examples=["08-01-2026", "15-03-2026"]
    ),
    end: str = Query(
        ...,
        description="End date in DD-MM-YYYY format (e.g., '10-01-2026')",
        examples=["10-01-2026", "20-03-2026"]
    ),
    cursor: Optional[str] = Query(
        None,
        description="Cursor for pagination (from previous response's next_cursor)",
        examples=[None, "eyJ0aW1lc3RhbXAiOiIyMDI2LTAxLTA4VDA4OjMwOjAwWiIsImlkIjoiYWJjMTIzIn0="]
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Number of results per page (default: 50, max: 100)",
        examples=[50, 25, 100]
    ),
    verified_user_id: str = Depends(verify_user_access),
    health_service: HealthService = Depends(get_health_service)
):
    """
    Get health data entries for the authenticated user within a date range with pagination.
    
    The verify_user_access dependency ensures the user can only see their own data.
    """
    # Parse date strings to datetime objects
    try:
        start_dt = health_service.parse_dd_mm_yyyy_date(start)
        end_dt = health_service.parse_dd_mm_yyyy_date(end)
    except InvalidDateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # Validate date range
    if start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start must be before or equal to end"
        )
    
    # Get health data with pagination
    entries, next_cursor, has_more = await health_service.get_health_data(
        user_id, start_dt, end_dt, cursor, limit
    )
    
    return PaginatedHealthDataResponse(
        data=entries,
        next_cursor=next_cursor,
        has_more=has_more,
        limit=limit
    )

@health_router.get(
    "/{user_id}/health-data/summary",
    response_model=HealthDataSummary,
    status_code=status.HTTP_200_OK,
    summary="Get summary of health data",
    description="""
    Retrieve a summary of health data for a user within a given date range.
    
    Returns:
    - `total_steps`: Total steps across all entries in the date range
    - `average_calories`: Average calories per entry
    - `averageSleepHours`: Average sleep hours per entry
    
    **Query Parameters:**
    - `start_date` (required): Start date in DD-MM-YYYY format (e.g., '08-01-2026')
    - `end_date` (required): End date in DD-MM-YYYY format (e.g., '10-01-2026')
    
    **Date Format:**
    - Only DD-MM-YYYY format is accepted (e.g., '08-01-2026' for January 8, 2026)
    - Dates are interpreted as midnight UTC
    
    **Security:**
    - Requires authentication
    - User can only retrieve their own health data entries
    """
)
async def get_health_data_summary(
    user_id: str,
    start_date: str = Query(
        ...,
        description="Start date in DD-MM-YYYY format (e.g., '08-01-2026')",
        examples=["08-01-2026", "15-03-2026"]
    ),
    end_date: str = Query(
        ...,
        description="End date in DD-MM-YYYY format (e.g., '10-01-2026')",
        examples=["10-01-2026", "20-03-2026"]
    ),
    verified_user_id: str = Depends(verify_user_access),
    health_service: HealthService = Depends(get_health_service)
):
    """
    Get a summary of health data for a user within a given date range.
    Dates must be in DD-MM-YYYY format.
    
    Authorization is verified by verify_user_access dependency.
    """
    # Parse date strings
    try:
        start_date_utc = health_service.parse_dd_mm_yyyy_date(start_date)
        end_date_utc = health_service.parse_dd_mm_yyyy_date(end_date)
    except InvalidDateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Validate date range
    if start_date_utc > end_date_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    try:
        return await health_service.get_health_data_summary(
            user_id,
            start_date_utc,
            end_date_utc
        )
    except HealthDataNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )