import asyncio
from pathlib import Path

from fastapi import HTTPException


async def stream_logs(file_path: Path):
    with open(file_path, "r") as file:
        for line in file:
            yield line
        
        while True:
            line = file.readline()
            if line:
                yield line
            else:
                await asyncio.sleep(0.1)