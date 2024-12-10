import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import config


LOGGING_PADDING = 8


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m",  # Reset color
    }

    def format(self, record):
        log_color = self.COLORS.get(
            record.levelname.strip("[]"), self.COLORS["RESET"]
        )  # noqa: E501
        levelname_padded = (
            f"{log_color}{record.levelname: <{LOGGING_PADDING}}"
            f"{self.COLORS['RESET']}"
        )
        record.levelname = levelname_padded
        return super().format(record)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    stdout: bool = True,
    filename: str | None = None,
    log_dir: Path | str | None = None,
    propagate: bool = False,
    datefmt: str = "%Y-%m-%d %H:%M:%S",
):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    log_format = "%(asctime)s %(levelname)s %(filename)s %(message)s"

    # File handler with rotation
    if filename is not None and not logger.handlers:
        log_path = config.LOGS_DIR / filename
        if log_dir is not None:
            log_dir = config.LOGS_DIR / log_dir
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

    # Stream handler for console output
    if stdout and not logger.handlers:
        color_formatter = ColoredFormatter(log_format, datefmt)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(color_formatter)
        logger.addHandler(console_handler)

    return logger
