import bpy  # noqa

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.config import config
from src.blender_service.router import router as blender_router


app = FastAPI()

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
