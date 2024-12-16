from enum import StrEnum


class JobErrorMessages(StrEnum):
    ZIP_FILE_REQUIRED = "Zip file is required."
    JOB_NOT_FOUND = "Job not found."
    JOB_ALREADY_RENDERING = "Job is already rendering."
    JOB_NOT_RENDERING = "Job is not rendering."
    SERVICE_BUSY = "Service is busy. Try later."
    LOG_FILE_NOT_FOUND = "Log file not found. Try later."


REDIS_PROGRESS_KEY = "render_progress:{}"
