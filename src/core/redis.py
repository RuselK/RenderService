from redis.asyncio import ConnectionPool, Redis

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
