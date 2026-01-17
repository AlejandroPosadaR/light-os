from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import verify_user_access
from app.models.health import (
    HealthDataCreate,
    HealthDataResponse,
    HealthDataSummary,
    PaginatedHealthDataResponse,
)
from app.services.health_service import (
    HealthService,
    InvalidDateError,
    get_health_service,
)

health_router = APIRouter(prefix="/users", tags=["health"])


@health_router.post(
    "/{user_id}/health-data",
    response_model=HealthDataResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_health_data(
    user_id: str,
    health_data: HealthDataCreate,
    verified_user_id: str = Depends(verify_user_access),
    health_service: HealthService = Depends(get_health_service)
):
    return await health_service.create_health_data(user_id, health_data)


@health_router.get(
    "/{user_id}/health-data",
    response_model=PaginatedHealthDataResponse
)
async def get_health_data(
    user_id: str,
    start: str = Query(..., description="Start date in DD-MM-YYYY format"),
    end: str = Query(..., description="End date in DD-MM-YYYY format"),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    verified_user_id: str = Depends(verify_user_access),
    health_service: HealthService = Depends(get_health_service)
):
    try:
        start_dt = health_service.parse_dd_mm_yyyy_date(start)
        end_dt = health_service.parse_dd_mm_yyyy_date(end)
    except InvalidDateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start must be before or equal to end"
        )
    
    return await health_service.get_health_data(user_id, start_dt, end_dt, cursor, limit)

@health_router.get(
    "/{user_id}/summary",
    response_model=HealthDataSummary
)
async def get_health_data_summary(
    user_id: str,
    start: str = Query(..., description="Start date in DD-MM-YYYY format"),
    end: str = Query(..., description="End date in DD-MM-YYYY format"),
    verified_user_id: str = Depends(verify_user_access),
    health_service: HealthService = Depends(get_health_service)
):
    try:
        start_dt = health_service.parse_dd_mm_yyyy_date(start)
        end_dt = health_service.parse_dd_mm_yyyy_date(end)
    except InvalidDateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start must be before or equal to end"
        )
    
    return await health_service.get_health_data_summary(user_id, start_dt, end_dt)