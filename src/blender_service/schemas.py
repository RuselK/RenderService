from uuid import uuid4
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Union

from fastapi import Depends
from redis.asyncio import Redis
from pydantic import BaseModel, ConfigDict, Field

from src.core.config import config
from src.core.redis import get_jobs_redis, RedisHandler


class OutputFormat(StrEnum):
    PNG = "PNG"
    JPEG = "JPEG"


class BlenderEngine(StrEnum):
    CYCLES = "CYCLES"
    EEVEE = "BLENDER_EEVEE_NEXT"


class Status(StrEnum):
    PENDING = "PENDING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class RenderResult(BaseModel):
    filename: str
    path: str
    timestamp: datetime


class SingleFrame(BaseModel):
    frame: int


class FrameRange(BaseModel):
    start: int
    end: int


class RenderSettings(BaseModel):
    frame_range: Union[FrameRange, SingleFrame]
    resolution_x: int = 1920
    resolution_y: int = 1080
    # camera_to_render: Union[str, None] = None # TODO: Add camera to render
    output_format: OutputFormat = OutputFormat.PNG
    engine: BlenderEngine = BlenderEngine.EEVEE

    model_config = ConfigDict(from_attributes=True)


class JobBase(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    model_config = ConfigDict(from_attributes=True)


class JobCreate(JobBase):
    zip_filename: str
    render_settings: Union[RenderSettings, None] = None
    status: Status = Status.PENDING


class JobRead(JobCreate):
    pass


class JobDB(JobCreate):

    @property
    def job_path(self) -> Path:
        return config.TEMP_DIR / self.job_id

    @property
    def extracted_dir(self) -> Path:
        return self.job_path / "extract"

    @property
    def rendered_dir(self) -> Path:
        return self.job_path / "rendered"

    @property
    def zip_file_path(self) -> Path:
        return self.job_path / self.zip_filename

    def init_dirs(self) -> None:
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        self.rendered_dir.mkdir(parents=True, exist_ok=True)


class JobManager:
    @classmethod
    def get(cls, job_id: str, redis: Redis = Depends(get_jobs_redis)) -> JobDB:
        job = RedisHandler.get(job_id, redis)
        if job:
            return JobDB.model_validate_json(job)
        return None

    @classmethod
    def save(cls, job: JobDB, redis: Redis = Depends(get_jobs_redis)) -> None:
        RedisHandler.save(job.job_id, job.model_dump_json(), redis)

    @classmethod
    def delete(
        cls, job_id: str, redis: Redis = Depends(get_jobs_redis)
    ) -> None:
        RedisHandler.delete(job_id, redis)
