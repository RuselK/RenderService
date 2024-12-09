from enum import Enum


class JobErrorMessages(Enum):
    ZIP_FILE_REQUIRED = "Zip file is required"
    JOB_NOT_FOUND = "Job not found"
    JOB_ALREADY_RENDERING = "Job is already rendering"
    SERVICE_BUSY = "Service is busy. Try later."
    LOG_FILE_NOT_FOUND = "Log file not found. Try later."
