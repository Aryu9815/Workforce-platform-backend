from app.core.config import settings
from app.core.logging_config import get_logger
import redis.asyncio as redis

logger = get_logger("redis")

class RedisManager():

    def __init__(self):
        self.redis_client: redis.Redis = None
    
    async def connect(self):
        try:
            self.redis_client = redis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connection established")
            return True
        
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without caching.")
            self.redis_client = None
            return False
    

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    async def clear_cache(self):
        if self.redis_client:
            await self.redis_client.flushdb()
            logger.info("Redis cache cleared")

redis_manager = RedisManager()