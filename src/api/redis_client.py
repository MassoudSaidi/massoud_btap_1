# redis_client.py

#import redis
import redis.asyncio as redis
import logging
from config import settings  

logger = logging.getLogger(__name__)

REDIS_HOST = settings.REDIS_ENDPOINT
REDIS_PORT = settings.REDIS_PORT

redis_client = None

try:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0?socket_connect_timeout=1&socket_timeout=1"
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Redis client configured successfully.")
except Exception as e:
    logger.error(f"Could not configure Redis client at startup: {e}")
    redis_client = None  # So we can detect failures elsewhere
