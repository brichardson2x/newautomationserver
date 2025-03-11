from app.core.config import settings
from app.core.logging import setup_logging
import subprocess

logger = setup_logging()

cmd = [
    "gunicorn",
    "-k", "uvicorn.workers.UvicornWorker",
    "-w", "4",
    "-b", f"{settings.FASTAPI_HOST}:{settings.FASTAPI_PORT}",
    "app.main:app"
]

logger.info("Starting Gunicorn")
subprocess.run(cmd)