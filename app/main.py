import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True
)
logging.getLogger("app.cache").setLevel(logging.INFO)

from fastapi import FastAPI, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers.auth import auth_router
from app.routers.health import health_router
from app.rate_limiter import rate_limit_middleware, load_rate_limit_script
from app.dependencies import auth_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load rate limit Lua script into Redis on startup."""
    await load_rate_limit_script()
    yield


app = FastAPI(title="Health API", version="1.0.0", lifespan=lifespan)

app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

app.include_router(auth_router)
app.include_router(health_router)


@app.get("/", response_model=dict, status_code=status.HTTP_200_OK)
def root() -> dict:
    return {"message": "Health API is running", "docs": "/docs"}


@app.get("/health", response_model=dict, status_code=status.HTTP_200_OK)
def health_check() -> dict:
    return {"status": "healthy"}