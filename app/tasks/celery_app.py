from celery import Celery
from app.core.config import settings

broker = settings.CELERY_BROKER_URL or "redis://redis:6379/0"
backend = settings.CELERY_RESULT_BACKEND or broker

celery_app = Celery("newautomationserver", broker=broker, backend=backend)
celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True
