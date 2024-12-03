from enum import StrEnum
from typing import Union

from pydantic import BaseModel, ConfigDict


class OutputFormat(StrEnum):
    PNG8bit = "PNG (8 bit)"
    PNG8bitAlpha = "PNG (8 bit + alpha)"
    PNG16bit = "PNG (16 bit)"
    PNG16bitAlpha = "PNG (16 bit + alpha)"
    JPEG = "JPEG"


class BlenderVersion(StrEnum):
    v4_3 = "4.3"


class BlenderEngine(StrEnum):
    CYCLES = "CYCLES"
    EEVEE = "EEVEE"


class SingleFrame(BaseModel):
    frame: int


class FrameRange(BaseModel):
    start: int
    end: int


class RenderSettings(BaseModel):
    frame_range: Union[FrameRange, SingleFrame]
    resolution_x: int = 1920
    resolution_y: int = 1080
    camera_to_render: Union[str, None] = None
    output_format: OutputFormat = OutputFormat.PNG8bit
    engine: BlenderEngine = BlenderEngine.EEVEE
    blender_version: BlenderVersion = BlenderVersion.v4_3

    model_config = ConfigDict(from_attributes=True)


class Status(StrEnum):
    PENDING = "PENDING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobBase(BaseModel):
    job_id: str
    model_config = ConfigDict(from_attributes=True)


class JobCreate(JobBase):
    zip_filename: str
    render_settings: Union[RenderSettings, None] = None
    status: Status = Status.PENDING


class JobRead(JobCreate):
    pass
