import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from .config import config


LOGGING_PADDING = 8
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(pathname)s - %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"
MAX_FILE_SIZE = 5 * 1024 * 1024
BACKUP_COUNT = 5


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        level_color = self.COLORS.get(record.levelname, self.RESET)
        levelname_padded = f"{record.levelname:<{LOGGING_PADDING}}"
        levelname_colored = f"{level_color}{levelname_padded}{self.RESET}"

        original_levelname = record.levelname
        record.levelname = levelname_colored
        formatted_message = super().format(record)
        record.levelname = original_levelname
        return formatted_message


def _create_file_handler(
    log_path: Path,
    level: int,
    log_format: str,
    datefmt: str,
    max_bytes: int = MAX_FILE_SIZE,
    backup_count: int = BACKUP_COUNT,
) -> RotatingFileHandler:
    """
    Create and return a rotating file handler with the given parameters.
    """
    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    formatter = logging.Formatter(log_format, datefmt)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def _create_console_handler(
    level: int, log_format: str, datefmt: str, use_color: bool = True
) -> logging.Handler:
    """
    Create and return a console (stream) handler.
    If use_color is True, applies colored formatting.
    """
    handler = logging.StreamHandler()
    if use_color:
        formatter = ColoredFormatter(log_format, datefmt)
    else:
        formatter = logging.Formatter(log_format, datefmt)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def setup_logger(
    name: str,
    level: int = logging.INFO,
    stdout: bool = True,
    filename: Optional[str] = None,
    log_dir: Optional[Union[Path, str]] = None,
    propagate: bool = False,
    datefmt: str = DEFAULT_DATEFMT,
    log_format: str = LOG_FORMAT,
    use_color: bool = True,
    max_file_size: int = MAX_FILE_SIZE,
    backup_count: int = BACKUP_COUNT,
) -> logging.Logger:
    """
    Set up and return a configured logger.

    :param name: The name of the logger.
    :param level: The logging level (e.g. logging.INFO).
    :param stdout: Whether to output to console.
    :param filename: If provided, a handler will be created with this filename.
    :param log_dir: Dir to store log, defaults to config.LOGS_DIR if not None.
    :param propagate: Whether to propagate logs to parent loggers.
    :param datefmt: Date format for log records.
    :param log_format: Format string for log messages.
    :param use_color: Whether to use colored output for console logs.
    :param max_file_size: Max size for rotating logs in bytes.
    :param backup_count: Number of backup files to keep.
    :return: A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    logger.handlers.clear()

    if filename:
        if log_dir is not None:
            log_dir_path = (
                (config.LOGS_DIR / log_dir)
                if isinstance(log_dir, str)
                else log_dir
            )
            log_dir_path.mkdir(parents=True, exist_ok=True)
            log_path = log_dir_path / filename
        else:
            log_path = config.LOGS_DIR / filename

        file_handler = _create_file_handler(
            log_path=log_path,
            level=level,
            log_format=log_format,
            datefmt=datefmt,
            max_bytes=max_file_size,
            backup_count=backup_count,
        )
        logger.addHandler(file_handler)

    if stdout:
        console_handler = _create_console_handler(
            level=level,
            log_format=log_format,
            datefmt=datefmt,
            use_color=use_color,
        )
        logger.addHandler(console_handler)

    return logger
