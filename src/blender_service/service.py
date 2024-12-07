import zipfile

from fastapi import Depends
from redis.asyncio import Redis
import bpy

from src.core.redis import get_jobs_redis
from .schemas import Status, JobManager, FrameRange, SingleFrame


async def unpack_zip(job_id: str, redis: Redis = Depends(get_jobs_redis)):
    job = await JobManager.get(job_id, redis)

    if not job:
        raise FileNotFoundError(f"Job not found: {job_id}")

    if not job.zip_file_path.exists():
        raise FileNotFoundError(f"Zip file not found: {job.zip_file_path}")

    job.init_dirs()

    with zipfile.ZipFile(job.zip_file_path, "r") as zip:
        zip.extractall(job.extracted_dir)


async def render_file(job_id: str, redis: Redis = Depends(get_jobs_redis)):
    try:
        await unpack_zip(job_id, redis)
        job = await JobManager.get(job_id, redis)

        blender_filename = None
        for file in job.extracted_dir.iterdir():
            if file.suffix == ".blend":
                blender_filename = file
                break

        if not blender_filename:
            raise FileNotFoundError(
                f"Blender file not found in {job.extracted_dir}"
            )

        blender_file_path = str(job.extracted_dir / blender_filename)

        bpy.ops.wm.open_mainfile(filepath=blender_file_path)

        bpy.context.scene.render.resolution_x = (
            job.render_settings.resolution_x
        )
        bpy.context.scene.render.resolution_y = (
            job.render_settings.resolution_y
        )

        bpy.context.scene.render.engine = job.render_settings.engine

        bpy.context.scene.render.image_settings.file_format = (
            job.render_settings.output_format
        )

        if job.render_settings.frame_range:
            if isinstance(job.render_settings.frame_range, FrameRange):
                bpy.context.scene.render.filepath = str(
                    job.rendered_dir / "frame_"
                )
                bpy.context.scene.frame_start = (
                    job.render_settings.frame_range.start
                )
                bpy.context.scene.frame_end = (
                    job.render_settings.frame_range.end
                )
                bpy.ops.render.render(animation=True)
            elif isinstance(job.render_settings.frame_range, SingleFrame):
                bpy.context.scene.render.filepath = str(
                    job.rendered_dir
                    / f"frame_{job.render_settings.frame_range.frame}.png"
                )
                bpy.context.scene.frame_set(
                    job.render_settings.frame_range.frame
                )
                bpy.ops.render.render(write_still=True)

        job.status = Status.COMPLETED
        await JobManager.save(job, redis)

    except Exception as e:
        job = await JobManager.get(job_id, redis)
        job.status = Status.FAILED
        await JobManager.save(job, redis)
        raise e  # TODO: DELETE
