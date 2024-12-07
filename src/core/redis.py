from redis.asyncio import ConnectionPool, Redis
from fastapi import Depends

from .config import config


def create_redis_pool(db: int) -> ConnectionPool:
    return ConnectionPool(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=db,
        encoding="utf-8",
        decode_responses=True,
    )


jobs_pool = create_redis_pool(config.REDIS_JOBS_DB)


async def get_jobs_redis() -> Redis:
    return Redis(connection_pool=jobs_pool)


class RedisHandler:

    @classmethod
    async def save(
        cls, key: str, data: str, redis: Redis = Depends(get_jobs_redis)
    ):
        await redis.set(key, data, ex=config.REDIS_DATA_LIFETIME)

    @classmethod
    async def get(cls, key: str, redis: Redis = Depends(get_jobs_redis)):
        data = await redis.get(key)
        if data:
            return data
        return None

    @classmethod
    async def delete(cls, key: str, redis: Redis = Depends(get_jobs_redis)):
        await redis.delete(key)
