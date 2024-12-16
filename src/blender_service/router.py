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
    JobRead,
    RenderSettings,
    Status,
    JobDB,
    RenderResult,
    ProjectDB,
    Project,
)
from .utils import JobManager, ProjectManager
from .dependencies import get_job_or_404, get_project_or_404, get_job_or_none
from .constants import JobErrorMessages
from .service import render_job


router = APIRouter(prefix="/renders", tags=["renders"])


@router.post("/{project_id}/upload", response_model=Project)
async def upload_file(
    zip_file: UploadFile,
    project_id: str,
    redis: Redis = Depends(get_jobs_redis),
):
    if zip_file.content_type not in [
        "application/zip",
        "application/x-zip-compressed",
    ] or not zip_file.filename.endswith(".zip"):
        raise BadRequestError(JobErrorMessages.ZIP_FILE_REQUIRED.value)

    project = ProjectDB(project_id=project_id, zip_filename=zip_file.filename)
    project.create_dirs()

    logger.info(
        f"Uploading file: {zip_file.filename} to {project.project_path}"
    )
    async with aiofiles.open(project.zip_file_path, "wb") as out_file:
        chunk_size = 1024 * 1024
        while True:
            chunk = await zip_file.read(chunk_size)
            if not chunk:
                break
            await out_file.write(chunk)

    logger.info(f"File uploaded: {zip_file.filename}")

    ProjectManager.save(project, redis)

    return project


@router.post("/job/{project_id}/start", response_model=JobRead)
def start_render(
    render_settings: RenderSettings,
    background_tasks: BackgroundTasks,
    request: Request,
    project: ProjectDB = Depends(get_project_or_404),
    redis: Redis = Depends(get_jobs_redis),
):
    if request.app.state.active_process is not None:
        raise BadRequestError(JobErrorMessages.SERVICE_BUSY.value)

    if not (config.TEMP_DIR / project.project_id).exists():
        raise BadRequestError(JobErrorMessages.PROJECT_NOT_FOUND.value)

    job = JobDB(
        project_id=project.project_id,
        render_settings=render_settings,
        status=Status.RENDERING,
    )

    JobManager.save(job, redis)

    background_tasks.add_task(render_job, job.job_id, request)
    return job


@router.post("/job/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_render(
    request: Request,
    job: JobDB = Depends(get_job_or_none),
    redis: Redis = Depends(get_jobs_redis),
):
    if job is not None and job.status == Status.RENDERING:
        job.status = Status.CANCELLED
        JobManager.save(job, redis)

    if (active_process := request.app.state.active_process) is None:
        raise BadRequestError(JobErrorMessages.JOB_NOT_RENDERING.value)

    active_process.kill()
    request.app.state.active_process = None


@router.get("/job/{job_id}/logs")
async def render_logs(job: JobDB = Depends(get_job_or_404)):

    log_dir = config.LOGS_DIR / "render_jobs"
    logs_file_path = log_dir / f"{job.job_id}.log"

    if not logs_file_path.exists():
        raise NotFoundError(JobErrorMessages.LOG_FILE_NOT_FOUND.value)

    return StreamingResponse(
        stream_logs(logs_file_path),
        media_type="text/plain",
    )


@router.get("/job/{job_id}/status", response_model=JobRead)
async def get_render_status(job: JobDB = Depends(get_job_or_404)):
    return job


@router.get("/job/{job_id}/result", response_model=list[RenderResult])
async def get_render_result(job: JobDB = Depends(get_job_or_404)):
    return await list_directory_files(
        job.rendered_dir, job.job_id, job.project_id
    )
