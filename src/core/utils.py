from datetime import datetime
from typing import AsyncGenerator
import asyncio
from pathlib import Path

from src.core.config import config


async def stream_logs(file_path: Path) -> AsyncGenerator[str, None]:
    with open(file_path, "r") as file:
        for line in file:
            yield line
        while True:
            line = file.readline()
            if line:
                yield line
            else:
                await asyncio.sleep(0.1)


async def list_directory_files(
    directory: Path, job_id: str, project_id: str
) -> list[dict]:
    files = []
    for file_path in directory.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append(
                {
                    "filename": file_path.name,
                    "path": (
                        f"{config.MEDIA_URL}/{project_id}/"
                        f"{job_id}/rendered/{file_path.name}"
                    ),
                    "timestamp": datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(),
                }
            )
    return files
