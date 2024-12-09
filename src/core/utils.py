import asyncio
from pathlib import Path


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


async def list_directory_files(directory: Path):
    files = []
    for file_path in directory.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "timestamp": stat.st_mtime
            })
    return files
