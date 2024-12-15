import argparse
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import time

import bpy
from bpy.app.handlers import persistent


BASE_DIR = Path(__file__).parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(pathname)s - %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    filename: str | None = None,
    log_dir: Path | str | None = None,
    datefmt: str = DEFAULT_DATEFMT,
    log_format: str = LOG_FORMAT,
):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if filename is not None:
        log_path = LOGS_DIR / filename
        if log_dir is not None:
            log_dir = LOGS_DIR / log_dir
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / filename

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
        )
        file_formatter = logging.Formatter(log_format, datefmt)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


service_logger = setup_logger(
    name="blender_service",
    level=logging.DEBUG,
    filename="blender_service.log",
)


def parce_args():
    service_logger.info("Start parsing arguments")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--job-id",
        type=str,
        required=True,
        help="Job ID",
    )
    parser.add_argument(
        "--blender-file-path",
        type=str,
        required=True,
        help="Path to the Blender file to render",
    )
    parser.add_argument(
        "--resolution-x",
        type=int,
        required=True,
        help="Resolution x",
    )
    parser.add_argument(
        "--resolution-y",
        type=int,
        required=True,
        help="Resolution y",
    )
    parser.add_argument(
        "--engine",
        type=str,
        required=True,
        help="Render engine",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        required=True,
        help="Output format",
    )
    parser.add_argument(
        "--frame-range",
        type=str,
        required=True,
        help="Frame or Frames to render",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where the rendered files will be saved.",
    )
    args = parser.parse_args()
    service_logger.info(f"Arguments parsed: {args}")
    return args


def render_blender_file(
    blender_file_path: str,
    resolution_x: int,
    resolution_y: int,
    engine: str,
    output_format: str,
    frame_range: int | list[int],
    rendered_dir: Path,
    logger: logging.Logger,
    job_id: str,
) -> None:
    filename = blender_file_path.split("/")[-1]

    @persistent
    def render_init_handler(scene):
        if isinstance(frame_range, list):
            frames = f"frames: {frame_range[0]}-{frame_range[-1]}"
        elif isinstance(frame_range, int):
            frames = f"frame: {frame_range.frame}"

        msg = (
            f"Start Render: {filename}, "
            f"resolution: {resolution_x}x{resolution_y}, "
            f"engine: {engine}, "
            f"output_format: {output_format}, "
            f"{frames}"
        )
        logger.info(msg)
        service_logger.info(f"Job ID: {job_id} - {msg}")

    @persistent
    def render_complete_handler(scene):
        msg = f"Render Completed: {filename}"
        logger.info(msg)
        service_logger.info(f"Job ID: {job_id} - {msg}")

    @persistent
    def render_write_handler(scene):
        msg = f"Write Frame: {scene.frame_current}"
        logger.info(msg)
        service_logger.info(f"Job ID: {job_id} - {msg}")

    @persistent
    def render_stats_handler(arg):
        msg = f"Render Stats: {arg}"
        logger.info(msg)
        service_logger.info(f"Job ID: {job_id} - {msg}")

    def clear_handlers():
        service_logger.debug("Clear bpy handlers")
        bpy.app.handlers.render_init.clear()
        bpy.app.handlers.render_complete.clear()
        bpy.app.handlers.render_write.clear()
        bpy.app.handlers.render_stats.clear()

    def add_handlers():
        service_logger.debug("Add bpy handlers")
        bpy.app.handlers.render_init.append(render_init_handler)
        bpy.app.handlers.render_complete.append(render_complete_handler)
        bpy.app.handlers.render_write.append(render_write_handler)
        bpy.app.handlers.render_stats.append(render_stats_handler)

    clear_handlers()
    add_handlers()

    service_logger.debug("Open Blender file")
    bpy.ops.wm.open_mainfile(filepath=blender_file_path)

    service_logger.debug("Set render settings")
    bpy.context.scene.render.resolution_x = resolution_x
    bpy.context.scene.render.resolution_y = resolution_y
    bpy.context.scene.render.engine = engine
    bpy.context.scene.render.image_settings.file_format = output_format

    if isinstance(frame_range, list):
        service_logger.debug(f"Set frame range: {frame_range}")
        bpy.context.scene.render.filepath = str(rendered_dir / "frame_")
        bpy.context.scene.frame_start = int(frame_range[0])
        bpy.context.scene.frame_end = int(frame_range[-1])
        status = bpy.ops.render.render(animation=True)
    elif isinstance(frame_range, int):
        service_logger.debug(f"Set frame range: {frame_range}")
        bpy.context.scene.render.filepath = str(
            rendered_dir / f"frame_{frame_range}.png"
        )
        bpy.context.scene.frame_set(int(frame_range))
        status = bpy.ops.render.render(write_still=True)

    bpy.ops.wm.quit_blender()

    return status


def main():
    args = parce_args()
    logger = setup_logger(
        name=args.job_id,
        filename=f"{args.job_id}.log",
        log_dir="render_jobs",
        log_format="%(asctime)s %(levelname)s %(message)s",
    )

    frame_range = args.frame_range.split(",")
    frame_range = map(int, frame_range)
    frame_range = list(frame_range)

    start_time = time.time()
    status = render_blender_file(
        blender_file_path=args.blender_file_path,
        resolution_x=args.resolution_x,
        resolution_y=args.resolution_y,
        engine=args.engine,
        output_format=args.output_format,
        frame_range=frame_range,
        rendered_dir=args.output_dir,
        logger=logger,
        job_id=args.job_id,
    )
    end_time = time.time()
    diff_time = round(end_time - start_time, 2)
    service_logger.info(
        f"Render status: {status}. Render time: {diff_time} sec."
        f"Job ID: {args.job_id}"
    )
    logger.info(f"Render time: {diff_time} sec.")


if __name__ == "__main__":
    main()
    # No other way to stop the process for eevee.
    raise KeyboardInterrupt
