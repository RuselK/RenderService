from fastapi import Depends
from redis import Redis

from src.core.redis import get_jobs_redis
from src.core.exceptions import NotFoundError
from .schemas import JobDB, ProjectDB
from .constants import JobErrorMessages
from .utils import JobManager, ProjectManager


async def get_job_or_404(
    job_id: str,
    redis: Redis = Depends(get_jobs_redis),
) -> JobDB:
    job = JobManager.get(job_id, redis)

    if not job:
        raise NotFoundError(JobErrorMessages.JOB_NOT_FOUND.value)
    return job


async def get_job_or_none(
    job_id: str,
    redis: Redis = Depends(get_jobs_redis),
) -> JobDB:
    job = JobManager.get(job_id, redis)
    return job


async def get_project_or_404(
    project_id: str,
    redis: Redis = Depends(get_jobs_redis),
) -> ProjectDB:
    project = ProjectManager.get(project_id, redis)

    if not project:
        raise NotFoundError(JobErrorMessages.PROJECT_NOT_FOUND.value)
    return project
