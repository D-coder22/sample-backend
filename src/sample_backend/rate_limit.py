import time
from uuid import uuid4

from fastapi import HTTPException, status
from services.redis import r

WINDOW = 60
MAX_CALLS = 5
SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
 
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
 
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_score = tonumber(oldest[2])
    local retry_after = math.ceil(window - (now - oldest_score))
    if retry_after < 1 then retry_after = 1 end
    return {0, retry_after}
end
 
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, window)
return {1, 0}
"""

check_script = r.register_script(SLIDING_WINDOW_SCRIPT)


async def check_rate_limit(idempotency_key: str) -> None:
    key = f"ratelimit:idem:{idempotency_key}"
    now = time.time()
    member = f"{now}-{uuid4().hex}"

    allowed, retry_after = await check_script(
        keys=[key], args=[now, WINDOW, MAX_CALLS, member]
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded for this Idempotency-Key: "
                f"max {MAX_CALLS} calls per {WINDOW}s."
            ),
            headers={"Retry-After": str(int(retry_after))},
        )
