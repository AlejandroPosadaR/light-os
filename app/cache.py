"""Simple Redis cache utilities with versioning support."""
# Standard library imports
import logging
import os
from typing import Optional

# Third-party imports
import redis

logger = logging.getLogger(__name__)
# Ensure logger is configured
logger.setLevel(logging.INFO)
logger.propagate = True

_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """
    Returns a Redis client if Redis is configured and reachable. Returns None if disabled.
    
    Works with:
    - Local Redis (docker-compose): Set REDIS_HOST=redis, REDIS_PORT=6379
    - Cloud Run Memorystore: Set REDIS_HOST=<memorystore-ip>, REDIS_PORT=6379
    """
    global _redis_client
    if _redis_client:
        return _redis_client

    host = os.getenv("REDIS_HOST")
    if not host:
        return None  # Redis is optional

    try:
        port = int(os.getenv("REDIS_PORT", "6379"))
        client = redis.Redis(
            host=host,
            port=port,
            decode_responses=False,  # Return bytes for Pydantic compatibility
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        client.ping()  # fail fast if unreachable
        _redis_client = client
        logger.info(f"Redis connected: {host}:{port}")
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed: {host}:{port} - {type(e).__name__}: {e}")
        return None


def get(key: str) -> Optional[bytes]:
    """Get value from cache (returns bytes for Pydantic compatibility)."""
    r = get_redis()
    if not r:
        return None
    value = r.get(key)
    found = value is not None
    # Log cache get operation
    logger.info(f"Getting key: {key}, found: {found}")
    return value


def set(key: str, value: bytes, ex: int = 60) -> None:
    """Set value in cache with expiration (accepts bytes for Pydantic compatibility)."""
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, ex, value)
        # Log cache set operation
        logger.info(f"Setting key: {key}, length: {len(value)} bytes, ttl: {ex}s")
    except Exception as e:
        logger.warning(f"Redis set failed for key {key}: {type(e).__name__}: {e}")


def delete(key: str) -> None:
    """Delete a key from cache."""
    r = get_redis()
    if not r:
        return
    r.delete(key)


def get_user_version(user_id: str) -> int:
    """Get cache version for a user. Initializes to 1 if missing."""
    r = get_redis()
    if not r:
        return 1

    key = f"version:{user_id}"
    version = r.get(key)

    if version is None:
        # Initialize atomically
        r.set(key, 1, nx=True)
        return 1

    return int(version)


def bump_user_version(user_id: str) -> None:
    """Increment cache version for a user (call on data writes)."""
    r = get_redis()
    if not r:
        return
    r.incr(f"version:{user_id}")
