from uuid import uuid4
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from src.core.config import config


class OutputFormat(StrEnum):
    PNG = "PNG"
    JPEG = "JPEG"


class BlenderEngine(StrEnum):
    CYCLES = "CYCLES"
    EEVEE = "BLENDER_EEVEE_NEXT"


class Status(StrEnum):
    PENDING = "PENDING"
    RENDERING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class RenderResult(BaseModel):
    filename: str
    path: str
    timestamp: datetime


class Project(BaseModel):
    project_id: str


class ProjectDB(Project):
    zip_filename: str

    @property
    def project_path(self) -> Path:
        return config.TEMP_DIR / self.project_id

    @property
    def extracted_dir(self) -> Path:
        return self.project_path / "extract"

    @property
    def zip_file_path(self) -> Path:
        return self.project_path / self.zip_filename

    def create_dirs(self) -> None:
        self.project_path.mkdir(parents=True, exist_ok=True)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)


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


class RenderProgress(BaseModel):
    current_frame: int
    total_frames: int
    remaining_frames: int


class JobBase(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    model_config = ConfigDict(from_attributes=True)


class JobCreate(JobBase):
    render_settings: Union[RenderSettings, None] = None
    status: Status = Status.PENDING
    render_progress: Union[RenderProgress, None] = None


class JobRead(JobCreate):
    pass


class JobDB(JobCreate):

    @property
    def project_path(self) -> Path:
        return config.TEMP_DIR / self.project_id

    @property
    def job_path(self) -> Path:
        return self.project_path / self.job_id

    @property
    def rendered_dir(self) -> Path:
        return self.job_path / "rendered"

    @property
    def zip_file_path(self) -> Path:
        return self.project_path / self.zip_filename

    def init_dirs(self) -> None:
        self.rendered_dir.mkdir(parents=True, exist_ok=True)
