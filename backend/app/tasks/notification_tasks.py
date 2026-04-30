from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)


def get_sync_db():
    with Session(sync_engine) as session:
        yield session


@celery_app.task
def send_notification(
    user_id: int,
    notification_type: str,
    title: str,
    content: str = None,
):
    """
    Create a notification record for a user.
    """
    from app.models.notification import Notification

    db = next(get_sync_db())
    try:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            content=content,
            is_read=False,
        )
        db.add(notification)
        db.commit()
        return {
            "status": "SUCCESS",
            "notification_id": notification.id,
            "user_id": user_id,
        }
    except Exception as exc:
        return {
            "status": "FAILURE",
            "user_id": user_id,
            "error": str(exc),
        }
    finally:
        db.close()


