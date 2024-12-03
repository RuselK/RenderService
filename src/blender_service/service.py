import zipfile

from fastapi import Depends
from redis.asyncio import Redis
import docker

from src.core.redis import get_jobs_redis
from src.core.config import config
from .schemas import JobRead, Status


client = docker.from_env()

image = "linuxserver/blender:4.3.0"


async def unpack_zip(job_id: str, redis: Redis = Depends(get_jobs_redis)):
    job_path = config.TEMP_DIR / job_id
    if not job_path.exists():
        raise FileNotFoundError(f"Job directory not found: {job_path}")

    # Create directories
    destination_dir = job_path / "extract"
    destination_dir.mkdir(parents=True, exist_ok=True)

    render_dir = job_path / "rendered"
    render_dir.mkdir(parents=True, exist_ok=True)

    # Unzip
    db_job = await redis.get(job_id)
    job = JobRead.model_validate_json(db_job)

    zip_file_path = job_path / job.zip_filename

    if not zip_file_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_file_path}")

    with zipfile.ZipFile(zip_file_path, "r") as zip:
        zip.extractall(destination_dir)


async def render_file(job_id: str, redis: Redis = Depends(get_jobs_redis)):
    try:
        db_job = await redis.get(job_id)
        job = JobRead.model_validate_json(db_job)
        await unpack_zip(job_id, redis)

        job_path = config.TEMP_DIR / job_id
        extracted_dir = job_path / "extract"
        render_dir = job_path / "rendered"

        volumes = {
            str(extracted_dir.resolve()): {"bind": "/input", "mode": "ro"},
            str(render_dir.resolve()): {"bind": "/output", "mode": "rw"},
        }

        device_requests = [
            docker.types.DeviceRequest(
                count=-1,
                driver="nvidia",
                capabilities=[
                    ["compute", "video", "graphics", "utility", "gpu"]
                ],
            )
        ]

        for blend_file in extracted_dir.glob("*.blend"):
            blender_command = [
                "--background",
                f"/input/{blend_file.name}",
                "--render-output",
                f"/output/{blend_file.stem}_####",
                "--render-format",
                "PNG",
                # "--engine", job.render_settings.engine.value,
                "--render-frame",
                "1",
                "--gpu-backend",
                "opengl",
            ]
            client.containers.run(
                image=image,
                command=blender_command,
                entrypoint="blender",
                # detach=False,
                # remove=True,
                volumes=volumes,
                device_requests=device_requests,
                environment={
                    "NVIDIA_VISIBLE_DEVICES": "all",
                    "NVIDIA_DRIVER_CAPABILITIES": "all",
                },
                tty=True,
                runtime="nvidia",
            )
        job.status = Status.COMPLETED

        await redis.set(
            job_id,
            job.model_dump_json(),
            ex=config.REDIS_DATA_LIFETIME,
        )

    except Exception as e:
        # Update job status to FAILED in case of an error
        db_job = await redis.get(job_id)
        job = JobRead.model_validate_json(db_job)
        job.status = Status.FAILED

        await redis.set(
            job_id,
            job.model_dump_json(),
            ex=config.REDIS_DATA_LIFETIME,
        )

        # Log the error
        print(f"Rendering failed for job {job_id}: {e}")

        # Re-raise the exception if needed
        raise


# async def render_file(job_id: str, redis: Redis = Depends(get_jobs_redis)):
#     try:
#         db_job = await redis.get(job_id)
#         if not db_job:
#             raise FileNotFoundError(f"Job not found: {job_id}")

#         job = JobRead.model_validate_json(db_job)

#         # Unzip files
#         zip_file_path = config.TEMP_DIR / job_id / job.zip_filename

#         if not zip_file_path.exists():
#             raise FileNotFoundError(f"Zip file not found: {zip_file_path}")

#         destination_dir = config.TEMP_DIR / job_id / "extracted"
#         destination_dir.mkdir(parents=True, exist_ok=True)

#         with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
#             zip_ref.extractall(destination_dir)

#         # Render files

#         render_dir = config.TEMP_DIR / job_id / "rendered"
#         render_dir.mkdir(parents=True, exist_ok=True)

#         for file in destination_dir.glob("*.blend"):
#             bpy.ops.wm.read_factory_settings(use_empty=True)
#             bpy.ops.wm.open_mainfile(filepath=str(file))
#             # bpy.context.scene.render.filepath = str(render_dir / file.stem)
#             # bpy.ops.render.render(write_still=True)

#             scene = bpy.context.scene
#             scene.render.image_settings.file_format = "PNG"
#             scene.render.filepath = str(render_dir / file.stem)

#             # Render the scene
#             bpy.ops.render.render(write_still=True)

#         # Save results

#         job.status = Status.COMPLETED

#         await redis.set(
#             job_id,
#             job.model_dump_json(),
#             ex=config.REDIS_DATA_LIFETIME,
#         )

#     except Exception:
#         db_job = await redis.get(job_id)

#         job = JobCreate.model_validate_json(db_job)
#         job.status = Status.FAILED

#         await redis.set(
#             job_id,
#             job.model_dump_json(),
#             ex=config.REDIS_DATA_LIFETIME,
#         )
#         raise
