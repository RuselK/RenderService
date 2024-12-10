from uuid import uuid4

from fastapi import APIRouter, UploadFile, Depends, status
from fastapi.responses import StreamingResponse
import aiofiles
from redis.asyncio import Redis

from src.core.config import config
from src.core.redis import get_jobs_redis
from src.core.celery import celery
from src.core.utils import stream_logs, list_directory_files
from src.core.exceptions import BadRequestError, NotFoundError
from .schemas import (
    JobBase,
    JobRead,
    RenderSettings,
    Status,
    JobDB,
    JobManager,
    RenderResult,
)
from .dependencies import get_job_or_404
from .constants import JobErrorMessages
from .service import render_job


router = APIRouter(prefix="/renders")


@router.post("/upload", response_model=JobBase)
async def upload_file(
    zip_file: UploadFile,
    redis: Redis = Depends(get_jobs_redis),
):
    if not zip_file.filename.endswith(".zip"):
        raise BadRequestError(JobErrorMessages.ZIP_FILE_REQUIRED.value)

    job_id = str(uuid4())

    job = JobDB(job_id=job_id, zip_filename=zip_file.filename)
    job.job_path.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(job.zip_file_path, "wb") as out_file:
        content = await zip_file.read()
        await out_file.write(content)

    JobManager.save(job, redis)

    return {"job_id": job_id}


@router.post("/{job_id}/start", response_model=JobRead)
def start_render(
    job_id: str,
    render_settings: RenderSettings,
    redis: Redis = Depends(get_jobs_redis),
):
    job = JobManager.get(job_id, redis)

    if not job:
        raise BadRequestError(JobErrorMessages.JOB_NOT_FOUND.value)

    if not (config.TEMP_DIR / job_id).exists():
        raise BadRequestError(JobErrorMessages.JOB_NOT_FOUND.value)

    # TODO: Temporaly disable this check
    # if job.status == Status.RENDERING:
    #     raise BadRequestError(JobErrorMessages.JOB_ALREADY_RENDERING.value)

    job.render_settings = render_settings
    job.status = Status.RENDERING

    JobManager.save(job, redis)

    render_job(job_id)

    return job


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_render(
    job: JobDB = Depends(get_job_or_404),
    redis: Redis = Depends(get_jobs_redis),
):
    if not job.task_id:
        raise BadRequestError(JobErrorMessages.JOB_NOT_RENDERING.value)

    celery.control.revoke(job.task_id, terminate=True)
    job.status = Status.CANCELLED
    JobManager.save(job, redis)


@router.get("/{job_id}/logs")
async def render_logs(job: JobDB = Depends(get_job_or_404)):

    log_dir = config.LOGS_DIR / "render_jobs"
    logs_file_path = log_dir / f"{job.job_id}.log"

    if not logs_file_path.exists():
        raise NotFoundError(JobErrorMessages.LOG_FILE_NOT_FOUND.value)

    return StreamingResponse(
        stream_logs(logs_file_path),
        media_type="text/plain",
    )


@router.get("/{job_id}/status", response_model=JobRead)
async def get_render_status(job: JobDB = Depends(get_job_or_404)):
    return job


@router.get("/{job_id}/result", response_model=list[RenderResult])
async def get_render_result(job: JobDB = Depends(get_job_or_404)):
    return await list_directory_files(job.rendered_dir, job.job_id)
