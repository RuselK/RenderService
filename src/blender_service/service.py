import zipfile
from pathlib import Path
import subprocess

from fastapi import Request

from src.core.redis import get_jobs_redis
from src.core.logger import setup_logger
from .exceptions import JobNotFoundError
from .schemas import (
    Status,
    JobManager,
    FrameRange,
    SingleFrame,
)


service_logger = setup_logger(
    name="blender_service",
    filename="blender_service.log",
)


def unpack_zip(zip_file_path: Path, extracted_dir: Path):
    service_logger.info(f"Unpack Zip: {zip_file_path}")
    if not zip_file_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_file_path}")

    with zipfile.ZipFile(zip_file_path, "r") as zip:
        zip.extractall(extracted_dir)
    service_logger.info(f"Unpack Zip Completed: {zip_file_path}")


def get_blender_file_path(extracted_dir: Path) -> Path:
    service_logger.info(f"Get Blender File Path: {extracted_dir}")
    blender_files = []

    for file in extracted_dir.iterdir():
        if file.suffix == ".blend":
            blender_files.append(file)

    if not blender_files:
        raise FileNotFoundError(f"Blender file not found in {extracted_dir}")

    if len(blender_files) > 1:
        raise ValueError(f"Multiple Blender files found in {extracted_dir}")

    service_logger.info(f"Blender File Path: {blender_files[0]}")
    return extracted_dir / blender_files[0]


def render_job(job_id: str, request: Request):
    logger = setup_logger(
        name=job_id,
        filename=f"{job_id}.log",
        log_dir="render_jobs",
        log_format="%(asctime)s %(levelname)s %(message)s",
    )
    redis = get_jobs_redis()
    try:
        job = JobManager.get(job_id, redis)

        if not job:
            raise JobNotFoundError(f"Job not found: {job_id}")

        if not job.extracted_dir.exists() and not job.rendered_dir.exists():
            job.init_dirs()

        if not any(job.extracted_dir.iterdir()):
            unpack_zip(job.zip_file_path, job.extracted_dir)

        blender_file_path = get_blender_file_path(job.extracted_dir)

        if isinstance(job.render_settings.frame_range, FrameRange):
            frame_range = (
                f"{job.render_settings.frame_range.start},"
                f"{job.render_settings.frame_range.end}"
            )
        elif isinstance(job.render_settings.frame_range, SingleFrame):
            frame_range = job.render_settings.frame_range.frame

        process = subprocess.Popen(
            [
                "python",
                "modules/render/run.py",
                "--job-id",
                job_id,
                "--blender-file-path",
                str(blender_file_path),
                "--resolution-x",
                str(job.render_settings.resolution_x),
                "--resolution-y",
                str(job.render_settings.resolution_y),
                "--engine",
                job.render_settings.engine.value,
                "--output-format",
                job.render_settings.output_format.value,
                "--frame-range",
                str(frame_range),
                "--output-dir",
                str(job.rendered_dir),
            ],
        )
        request.app.state.active_process = process
        process.wait()

        job = JobManager.get(job_id, redis)
        if job.status == Status.CANCELLED:
            service_logger.info(f"Render Job Cancelled: {job_id}")
            logger.info("Render Job Cancelled.")
            return

        service_logger.info(f"Updating Job Status to COMPLETED: {job_id}")
        job.status = Status.COMPLETED
        request.app.state.active_process = None
        JobManager.save(job, redis)
        service_logger.info(f"Render Job Completed: {job_id}")

    except JobNotFoundError:
        service_logger.error(f"Job not found: {job_id}")
    except Exception as exc:
        job = JobManager.get(job_id, redis)
        job.status = Status.FAILED
        job.task_id = None
        JobManager.save(job, redis)

        service_logger.error(f"Render Failed: {exc}, job_id: {job_id}")
        logger.error("Render Failed.")
