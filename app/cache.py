import logging
import os
import redis

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    """Get Redis client singleton. Returns None if Redis is not configured."""
    global _redis_client
    if _redis_client:
        return _redis_client

    host = os.getenv("REDIS_HOST")
    if not host:
        return None

    try:
        port = int(os.getenv("REDIS_PORT", "6379"))
        client = redis.Redis(
            host=host,
            port=port,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        client.ping()
        _redis_client = client
        logger.info(f"Redis connected: {host}:{port}")
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed: {host}:{port} - {type(e).__name__}: {e}")
        return None


def get(key: str) -> bytes | None:
    """Get value from cache."""
    r = get_redis()
    if not r:
        return None
    value = r.get(key)
    logger.info(f"Getting key: {key}, found: {value is not None}")
    return value


def set(key: str, value: bytes, ex: int = 60) -> None:
    """Set value in cache with expiration."""
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, ex, value)
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
        r.set(key, 1, nx=True)
        return 1

    return int(version)


def bump_user_version(user_id: str) -> None:
    """Increment cache version for a user."""
    r = get_redis()
    if not r:
        return
    r.incr(f"version:{user_id}")
