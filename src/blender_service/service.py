import zipfile
from pathlib import Path
import logging

import bpy
from bpy.app.handlers import persistent

from src.core.redis import get_jobs_redis
from src.core.logger import setup_logger
from .schemas import (
    Status,
    JobManager,
    FrameRange,
    SingleFrame,
    JobDB,
    BlenderEngine,
    OutputFormat,
)


def unpack_zip(zip_file_path: Path, extracted_dir: Path):
    if not zip_file_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_file_path}")

    with zipfile.ZipFile(zip_file_path, "r") as zip:
        zip.extractall(extracted_dir)


def get_blender_file_path(extracted_dir: Path) -> Path:
    blender_files = []

    for file in extracted_dir.iterdir():
        if file.suffix == ".blend":
            blender_files.append(file)

    if not blender_files:
        raise FileNotFoundError(
            f"Blender file not found in {extracted_dir}"
        )
    if len(blender_files) > 1:
        raise ValueError(
            f"Multiple Blender files found in {extracted_dir}"
        )
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
    @persistent
    def render_init_handler(scene):
        if logger:
            if isinstance(frame_range, FrameRange):
                frames = f"frames: {frame_range.start}-{frame_range.end}"
            elif isinstance(frame_range, SingleFrame):
                frames = f"frame: {frame_range.frame}"

            logger.info(
                f"Start Render: {blender_file_path.split('/')[-1]}, "
                f"resolution: {resolution_x}x{resolution_y}, "
                f"engine: {engine}, "
                f"output_format: {output_format}, "
                f"{frames}"
            )

    @persistent
    def render_complete_handler(scene):
        if logger:
            logger.info(
                f"Render Completed: {blender_file_path.split('/')[-1]}"
            )

    @persistent
    def render_write_handler(scene):
        if logger:
            logger.info(f"Write Frame: {scene.frame_current}")

    bpy.app.handlers.render_init.append(render_init_handler)
    bpy.app.handlers.render_complete.append(render_complete_handler)
    bpy.app.handlers.render_write.append(render_write_handler)

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
    # TODO: Logger is dublicating logs. Fix it.
    logger = setup_logger(
        name=job_id,
        filename=f"{job_id}.log",
    )
    try:
        redis = get_jobs_redis()
        job = JobManager.get(job_id, redis)

        job.init_dirs()

        if not job:
            raise FileNotFoundError(f"Job not found: {job_id}")

        unpack_zip(job.zip_file_path, job.extracted_dir)

        blender_file_path = get_blender_file_path(job.extracted_dir)

        render_blender_file(
            blender_file_path=str(blender_file_path),
            resolution_x=job.render_settings.resolution_x,
            resolution_y=job.render_settings.resolution_y,
            engine=job.render_settings.engine,
            output_format=job.render_settings.output_format,
            frame_range=job.render_settings.frame_range,
            rendered_dir=job.rendered_dir,
            logger=logger,
        )

        job.status = Status.COMPLETED
        JobManager.save(job, redis)

    except Exception as exc:
        logger.error(f"Render Failed: {exc}")

        redis = get_jobs_redis()
        job = JobManager.get(job_id, redis)
        job.status = Status.FAILED
        JobManager.save(job, redis)
