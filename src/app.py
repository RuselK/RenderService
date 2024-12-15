from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.logger import logger

from src.core.logger import _create_file_handler, DEFAULT_DATEFMT, LOG_FORMAT
from src.core.config import config
from src.blender_service.router import router as blender_router


file_handler = _create_file_handler(
    log_path=config.LOGS_DIR / "app.log",
    level=logging.INFO,
    log_format=LOG_FORMAT,
    datefmt=DEFAULT_DATEFMT,
)
logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.active_process = None
    yield
    app.state.active_process = None


app = FastAPI(
    lifespan=lifespan,
    title="Render Service",
    description="Render Service",
    version="0.1.1",  # Updated 2024-12-15
)

# Routes
api_router = APIRouter(prefix="/api")
api_router.include_router(blender_router)

# App
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=config.CORS_METHODS,
    allow_headers=config.CORS_HEADERS,
)
app.include_router(api_router)
app.mount("/media", StaticFiles(directory=config.TEMP_DIR), name="media")
