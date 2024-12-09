from fastapi import Depends
from redis import Redis

from src.blender_service.schemas import JobManager, JobDB
from src.core.redis import get_jobs_redis
from src.core.exceptions import NotFoundError
from .constants import JobErrorMessages


async def get_job_or_404(
    job_id: str,
    redis: Redis = Depends(get_jobs_redis),
) -> JobDB:
    job = JobManager.get(job_id, redis)

    if not job:
        raise NotFoundError(JobErrorMessages.JOB_NOT_FOUND.value)
    return job
