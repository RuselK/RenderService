from uuid import uuid4

from fastapi import (
    APIRouter,
    UploadFile,
    HTTPException,
    Depends,
    BackgroundTasks,
)
import aiofiles
from redis.asyncio import Redis

from src.core.config import config
from src.core.redis import get_jobs_redis
from .schemas import JobBase, JobCreate, JobRead, RenderSettings, Status
from .service import render_file


router = APIRouter(prefix="/renders")


@router.post("/upload", response_model=JobBase)
async def upload_file(
    zip_file: UploadFile,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_jobs_redis),
):
    if not zip_file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Zip file is required",
        )

    job_id = str(uuid4())

    out_path = config.TEMP_DIR / job_id
    out_path.mkdir(parents=True, exist_ok=True)
    out_file_path = out_path / zip_file.filename

    async with aiofiles.open(out_file_path, "wb") as out_file:
        content = await zip_file.read()
        await out_file.write(content)

    await redis.set(
        job_id,
        JobCreate(
            job_id=job_id,
            zip_filename=zip_file.filename,
        ).model_dump_json(),
        ex=config.REDIS_DATA_LIFETIME,
    )

    # background_tasks.add_task(unpack_zip, job_id, redis)

    return {"job_id": job_id}


@router.post("/{job_id}/start", response_model=JobRead)
async def start_render(
    job_id: str,
    render_settings: RenderSettings,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_jobs_redis),
):
    # TODO: Check if service is busy. If yes, raise 400.

    db_job = await redis.get(job_id)

    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not (config.TEMP_DIR / job_id).exists():
        raise HTTPException(status_code=404, detail="Job not found")

    job = JobCreate.model_validate_json(db_job)

    # if job.status == Status.RENDERING:
    #     raise HTTPException(
    # status_code=400, detail="Job is already rendering")

    job.render_settings = render_settings.model_dump(exclude_none=True)
    job.status = Status.RENDERING

    await redis.set(
        job_id,
        job.model_dump_json(),
        ex=config.REDIS_DATA_LIFETIME,
    )

    await render_file(job_id, redis)

    # background_tasks.add_task(render_file, job_id, redis)

    return job


# TODO implement long polling for render logs
@router.get("/{job_id}/logs")
async def render_logs(job_id: str, redis: Redis = Depends(get_jobs_redis)):
    pass


# @router.post("/{job_id}/cancel")
# async def cancel_render(job_id: str):
#     pass


# @router.get("/{job_id}/status")
# async def get_render_status(job_id: str):
#     pass


# @router.get("/{job_id}/result")
# async def get_render_result(job_id: str):
#     pass
