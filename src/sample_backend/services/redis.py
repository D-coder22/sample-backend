from config import REDIS_HOST, REDIS_PORT
from redis.asyncio import Redis

r = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_keepalive=True,
)
