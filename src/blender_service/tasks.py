from src.core.celery import celery
from .service import render_job


@celery.task
def render_job_task(job_id: str):
    render_job(job_id)
    return True
