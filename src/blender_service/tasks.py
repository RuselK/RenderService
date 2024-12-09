from src.core.celery import celery
from .service import render_job, service_logger


@celery.task
def render_job_task(job_id: str):
    service_logger.info(f"Starting task: {job_id}")
    render_job(job_id)
    service_logger.info(f"Task finished: {job_id}")
    return True
