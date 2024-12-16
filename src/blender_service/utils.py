from fastapi import Depends
from redis import Redis

from src.core.redis import get_jobs_redis, RedisHandler
from .schemas import JobDB, RenderProgress, ProjectDB
from .constants import REDIS_PROGRESS_KEY


class ProjectManager:
    @classmethod
    def get(
        cls, project_id: str, redis: Redis = Depends(get_jobs_redis)
    ) -> ProjectDB:
        project_data = RedisHandler.get(project_id, redis)
        if not project_data:
            return None
        return ProjectDB.model_validate_json(project_data)

    @classmethod
    def save(
        cls, project: ProjectDB, redis: Redis = Depends(get_jobs_redis)
    ) -> None:
        RedisHandler.save(project.project_id, project.model_dump_json(), redis)

    @classmethod
    def delete(
        cls, project_id: str, redis: Redis = Depends(get_jobs_redis)
    ) -> None:
        RedisHandler.delete(project_id, redis)


class JobManager:
    @classmethod
    def get(cls, job_id: str, redis: Redis = Depends(get_jobs_redis)) -> JobDB:
        job_data = RedisHandler.get(job_id, redis)
        progress = RedisHandler.get(REDIS_PROGRESS_KEY.format(job_id), redis)
        if not job_data:
            return None

        job = JobDB.model_validate_json(job_data)
        if progress:
            job.render_progress = RenderProgress.model_validate_json(progress)
        return job

    @classmethod
    def save(cls, job: JobDB, redis: Redis = Depends(get_jobs_redis)) -> None:
        RedisHandler.save(job.job_id, job.model_dump_json(), redis)

    @classmethod
    def delete(
        cls, job_id: str, redis: Redis = Depends(get_jobs_redis)
    ) -> None:
        RedisHandler.delete(job_id, redis)
