from celery import Celery

from src.core.config import config


celery = Celery(
    "tasks",
    broker=config.CELERY_REDIS_URL,
    backend=config.CELERY_REDIS_URL,
)

celery.autodiscover_tasks(["src.blender_service.tasks"])
