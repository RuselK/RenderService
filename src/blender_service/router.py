from fastapi import (
    APIRouter,
    UploadFile,
    Depends,
    status,
    BackgroundTasks,
    Request,
)
from fastapi.responses import StreamingResponse
from fastapi.logger import logger
import aiofiles
from redis.asyncio import Redis

from src.core.config import config
from src.core.redis import get_jobs_redis
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


router = APIRouter(prefix="/renders", tags=["renders"])


@router.post("/upload", response_model=JobBase)
async def upload_file(
    zip_file: UploadFile,
    redis: Redis = Depends(get_jobs_redis),
):
    if zip_file.content_type not in [
        "application/zip",
        "application/x-zip-compressed",
    ] or not zip_file.filename.endswith(".zip"):
        raise BadRequestError(JobErrorMessages.ZIP_FILE_REQUIRED.value)

    job = JobDB(zip_filename=zip_file.filename)
    job.job_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Uploading file: {zip_file.filename}")
    async with aiofiles.open(job.zip_file_path, "wb") as out_file:
        chunk_size = 1024 * 1024
        while True:
            chunk = await zip_file.read(chunk_size)
            if not chunk:
                break
            await out_file.write(chunk)

    logger.info(f"File uploaded: {zip_file.filename}")

    JobManager.save(job, redis)

    return job


@router.post("/{job_id}/start", response_model=JobRead)
def start_render(
    render_settings: RenderSettings,
    background_tasks: BackgroundTasks,
    request: Request,
    job: JobDB = Depends(get_job_or_404),
    redis: Redis = Depends(get_jobs_redis),
):
    if request.app.state.active_process is not None:
        raise BadRequestError(JobErrorMessages.SERVICE_BUSY.value)

    if not (config.TEMP_DIR / job.job_id).exists():
        raise BadRequestError(JobErrorMessages.JOB_NOT_FOUND.value)

    if job.status == Status.RENDERING:
        raise BadRequestError(JobErrorMessages.JOB_ALREADY_RENDERING.value)

    job.render_settings = render_settings
    job.status = Status.RENDERING

    JobManager.save(job, redis)

    background_tasks.add_task(render_job, job.job_id, request)
    return job


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_render(
    request: Request,
    job: JobDB = Depends(get_job_or_404),
    redis: Redis = Depends(get_jobs_redis),
):
    if job.status == Status.RENDERING:
        job.status = Status.CANCELLED
        JobManager.save(job, redis)

    if (active_process := request.app.state.active_process) is None:
        raise BadRequestError(JobErrorMessages.JOB_NOT_RENDERING.value)

    active_process.kill()
    request.app.state.active_process = None


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
