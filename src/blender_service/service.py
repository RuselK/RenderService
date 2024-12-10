import zipfile
from pathlib import Path
import subprocess

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


def render_job(job_id: str):
    logger = setup_logger(
        name=job_id, filename=f"{job_id}.log", log_dir="render_jobs"
    )
    try:
        redis = get_jobs_redis()
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
        else:
            raise ValueError(
                f"Invalid frame range: {job.render_settings.frame_range}"
            )

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
        process.wait()

        service_logger.info(f"Update Job Status: {job_id}")

        job.status = Status.COMPLETED
        job.task_id = None
        JobManager.save(job, redis)

        service_logger.info(f"Render Job Completed: {job_id}")

    except JobNotFoundError as exc:
        raise exc
    except Exception as exc:
        redis = get_jobs_redis()
        job = JobManager.get(job_id, redis)
        job.status = Status.FAILED
        job.task_id = None
        JobManager.save(job, redis)

        service_logger.error(f"Render Failed: {exc}, job_id: {job_id}")
        logger.error("Render Failed.")
