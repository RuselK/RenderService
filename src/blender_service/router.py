from uuid import uuid4

from fastapi import (
    APIRouter,
    UploadFile,
    HTTPException,
    Depends,
)
from fastapi.responses import StreamingResponse
import aiofiles
from redis.asyncio import Redis

from src.core.config import config
from src.core.redis import get_jobs_redis
from src.core.celery import celery
from src.core.utils import stream_logs
from .schemas import (
    JobBase,
    JobRead,
    RenderSettings,
    Status,
    JobDB,
    JobManager,
)
from .tasks import render_job_task

router = APIRouter(prefix="/renders")


@router.post("/upload", response_model=JobBase)
async def upload_file(
    zip_file: UploadFile,
    redis: Redis = Depends(get_jobs_redis),
):
    if not zip_file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Zip file is required",
        )

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
    inspector = celery.control.inspect()
    active_tasks = inspector.active()
    if active_tasks and any(active_tasks.values()):
        raise HTTPException(
            status_code=400,
            detail="Service is busy. Try later.",
        )

    job = JobManager.get(job_id, redis)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not (config.TEMP_DIR / job_id).exists():
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == Status.RENDERING:
        raise HTTPException(
            status_code=400, detail="Job is already rendering"
        )

    job.render_settings = render_settings
    job.status = Status.RENDERING

    JobManager.save(job, redis)

    render_job_task.delay(job_id)

    return job


@router.get("/{job_id}/logs")
async def render_logs(job_id: str, redis: Redis = Depends(get_jobs_redis)):
    job = JobManager.get(job_id, redis)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    logs_file_path = config.LOGS_DIR / f"{job.job_id}.log"

    if not logs_file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Log file not found. Try later.",
        )

    return StreamingResponse(
        stream_logs(logs_file_path),
        media_type="text/plain",
    )


@router.get("/{job_id}/status", response_model=JobRead)
async def get_render_status(
    job_id: str,
    redis: Redis = Depends(get_jobs_redis),
):
    job = JobManager.get(job_id, redis)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


# @router.get("/{job_id}/result")
# async def get_render_result(job_id: str):
#     pass
