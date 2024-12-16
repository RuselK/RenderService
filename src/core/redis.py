import logging

from redis import ConnectionPool, Redis
from fastapi import Depends

from .config import config
from .logger import setup_logger

logger = setup_logger(
    name="redis",
    level=logging.DEBUG,
    filename="redis.log",
    stdout=False,
)


def create_redis_pool(db: int) -> ConnectionPool:
    logger.debug(f"Creating Redis pool for db: {db}")
    return ConnectionPool(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=db,
        encoding="utf-8",
        decode_responses=True,
    )


jobs_pool = create_redis_pool(config.REDIS_JOBS_DB)


def get_jobs_redis() -> Redis:
    logger.debug("Getting Redis connection for jobs")
    return Redis(connection_pool=jobs_pool)


class RedisHandler:

    @classmethod
    def save(cls, key: str, data: str, redis: Redis = Depends(get_jobs_redis)):
        logger.debug(f"Saving data to Redis: key={key}, data={data}")
        redis.set(key, data, ex=config.REDIS_DATA_LIFETIME)

    @classmethod
    def get(cls, key: str, redis: Redis = Depends(get_jobs_redis)):
        logger.debug(f"Getting data from Redis: key={key}")
        data = redis.get(key)
        logger.debug(f"Data retrieved from Redis: key={key}, data={data}")
        if data:
            return data
        return None

    @classmethod
    def delete(cls, key: str, redis: Redis = Depends(get_jobs_redis)):
        logger.debug(f"Deleting data from Redis: key={key}")
        redis.delete(key)
