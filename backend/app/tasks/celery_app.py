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
    beat_schedule={
        'check-due-matters': {
            'task': 'app.tasks.notification_tasks.check_due_matters',
            'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
        },
        'check-stalled-matters': {
            'task': 'app.tasks.notification_tasks.check_stalled_matters',
            'schedule': crontab(hour=8, minute=30),  # Daily at 8:30 AM
        },
        'check-sla-overdue': {
            'task': 'app.tasks.notification_tasks.check_sla_overdue',
            'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks.preview_tasks", "app.tasks.archive_tasks", "app.tasks.search_tasks", "app.tasks.notification_tasks"])
