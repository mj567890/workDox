from app.config import get_settings
from celery import Celery
from celery.schedules import crontab

settings = get_settings()

celery_app = Celery(
    "odms",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,
    beat_schedule={},
)

celery_app.autodiscover_tasks(["app.tasks.preview_tasks", "app.tasks.archive_tasks", "app.tasks.search_tasks", "app.tasks.notification_tasks", "app.tasks.embedding_tasks"])
