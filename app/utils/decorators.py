from app.core.redis_manager import redis_manager

def redis_required(func):
    async def wrapper(self, *args, **kwargs):
        client = redis_manager.redis_client
        if not client:
            return None
        return await func(self, *args, **kwargs)
    return wrapper