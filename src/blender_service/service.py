import zipfile
from pathlib import Path
import logging
import subprocess

import bpy
from bpy.app.handlers import persistent

from src.core.redis import get_jobs_redis
from src.core.logger import setup_logger
from .exceptions import JobNotFoundError
from .schemas import (
    Status,
    JobManager,
    FrameRange,
    SingleFrame,
    BlenderEngine,
    OutputFormat,
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


def render_blender_file(
    blender_file_path: str,
    resolution_x: int,
    resolution_y: int,
    engine: BlenderEngine,
    output_format: OutputFormat,
    frame_range: FrameRange | SingleFrame,
    rendered_dir: Path,
    logger: logging.Logger | None = None,
):
    filename = blender_file_path.split("/")[-1]

    @persistent
    def render_init_handler(scene):
        if logger:
            if isinstance(frame_range, FrameRange):
                frames = f"frames: {frame_range.start}-{frame_range.end}"
            elif isinstance(frame_range, SingleFrame):
                frames = f"frame: {frame_range.frame}"

            msg = (
                f"Start Render: {filename}, "
                f"resolution: {resolution_x}x{resolution_y}, "
                f"engine: {engine}, "
                f"output_format: {output_format}, "
                f"{frames}"
            )
            service_logger.info(msg)

            logger.info(msg)

    @persistent
    def render_complete_handler(scene):
        if logger:
            msg = f"Render Completed: {filename}"
            service_logger.info(msg)
            logger.info(msg)

    @persistent
    def render_write_handler(scene):
        if logger:
            msg = f"Write Frame: {scene.frame_current}"
            service_logger.info(msg + f" filename: {filename}")
            logger.info(msg)

    @persistent
    def render_stats_handler(arg):
        if logger:
            msg = f"Render Stats: {arg}"
            service_logger.info(msg)
            logger.info(msg)

    bpy.app.handlers.render_init.clear()
    bpy.app.handlers.render_complete.clear()
    bpy.app.handlers.render_write.clear()
    bpy.app.handlers.render_stats.clear()

    bpy.app.handlers.render_init.append(render_init_handler)
    bpy.app.handlers.render_complete.append(render_complete_handler)
    bpy.app.handlers.render_write.append(render_write_handler)
    bpy.app.handlers.render_stats.append(render_stats_handler)

    bpy.ops.wm.open_mainfile(filepath=blender_file_path)

    bpy.context.scene.render.resolution_x = resolution_x
    bpy.context.scene.render.resolution_y = resolution_y

    bpy.context.scene.render.engine = engine

    bpy.context.scene.render.image_settings.file_format = output_format

    if isinstance(frame_range, FrameRange):
        bpy.context.scene.render.filepath = str(rendered_dir / "frame_")
        bpy.context.scene.frame_start = frame_range.start
        bpy.context.scene.frame_end = frame_range.end
        bpy.ops.render.render(animation=True)
    elif isinstance(frame_range, SingleFrame):
        bpy.context.scene.render.filepath = str(
            rendered_dir / f"frame_{frame_range.frame}.png"
        )
        bpy.context.scene.frame_set(frame_range.frame)
        bpy.ops.render.render(write_still=True)
    else:
        raise ValueError(f"Invalid frame range: {frame_range}")


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

        print(f"Render Job: {job_id}")

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
