import os
import time
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis

logger = logging.getLogger(__name__)

DISABLE_RATE_LIMIT = os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true"

AUTH_RATE = 2.0
AUTH_CAPACITY = 30
ANON_RATE = 0.5
ANON_CAPACITY = 10

TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local tokens_requested = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

local elapsed = now - last_refill
local tokens_to_add = elapsed * rate
tokens = math.min(capacity, tokens + tokens_to_add)

if tokens < tokens_requested then
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 120)
    return 0
end

tokens = tokens - tokens_requested
redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
redis.call('EXPIRE', key, 120)
return 1
"""

_redis_client: redis.Redis | None = None
_script_sha: str | None = None


async def get_redis_client() -> redis.Redis | None:
    """Get async Redis client singleton for rate limiting."""
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
        await client.ping()
        _redis_client = client
        logger.info(f"Rate limiter Redis connected: {host}:{port}")
        return client
    except Exception as e:
        logger.warning(f"Rate limiter Redis connection failed: {host}:{port} - {type(e).__name__}: {e}")
        return None


async def load_rate_limit_script() -> str | None:
    """Load Lua script into Redis and return SHA. Call on startup."""
    global _script_sha
    if _script_sha:
        return _script_sha

    redis_client = await get_redis_client()
    if not redis_client:
        logger.warning("Redis not available, rate limiting disabled")
        return None

    try:
        _script_sha = await redis_client.script_load(TOKEN_BUCKET_SCRIPT)
        logger.info(f"Rate limit script loaded: {_script_sha[:8]}...")
        return _script_sha
    except Exception as e:
        logger.warning(f"Failed to load rate limit script: {e}")
        return None


def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(identifier: str, rate: float, capacity: int, script_sha: str | None, tokens_requested: int = 1) -> bool:
    """Check rate limit using token bucket. Returns True if allowed, False if limited."""
    redis_client = await get_redis_client()
    if not redis_client or not script_sha:
        return True

    key = f"ratelimit:{identifier}"
    now = time.time()

    try:
        result = await redis_client.evalsha(script_sha, 1, key, capacity, rate, now, tokens_requested)
        return bool(result)
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return True


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware using token bucket algorithm."""
    if DISABLE_RATE_LIMIT:
        return await call_next(request)

    user_id = getattr(request.state, "user_id", None)
    if user_id:
        identifier = f"user:{user_id}"
        rate = AUTH_RATE
        capacity = AUTH_CAPACITY
    else:
        identifier = f"ip:{get_client_ip(request)}"
        rate = ANON_RATE
        capacity = ANON_CAPACITY

    script_sha = _script_sha
    if not script_sha or not await check_rate_limit(identifier, rate, capacity, script_sha):
        if not script_sha:
            return await call_next(request)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60"}
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(int(capacity))
    response.headers["X-RateLimit-Rate"] = f"{rate:.1f}/s"
    response.headers["X-RateLimit-Burst"] = str(int(capacity))
    return response
