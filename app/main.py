import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True
)
# Ensure app.cache logger is configured
logging.getLogger("app.cache").setLevel(logging.INFO)

from fastapi import FastAPI, status
from app.routers.auth import auth_router
from app.routers.health import health_router

app = FastAPI(title="Health API", version="1.0.0")

app.include_router(auth_router)
app.include_router(health_router)


@app.get("/", response_model=dict, status_code=status.HTTP_200_OK)
def root() -> dict:
    """Root endpoint with API information."""
    return {"message": "Health API is running", "docs": "/docs"}


@app.get("/health", response_model=dict, status_code=status.HTTP_200_OK)
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}