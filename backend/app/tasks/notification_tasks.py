from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine, select, func, or_
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
    matter_id: int = None,
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
            related_matter_id=matter_id,
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


@celery_app.task
def check_due_matters():
    """
    Check for matters approaching deadline or overdue.
    Creates notifications for matter owners.

    Intended to be called by Celery Beat on a regular schedule (e.g., daily).
    """
    from app.models.matter import Matter

    db = next(get_sync_db())
    try:
        now = datetime.now(timezone.utc)
        near_deadline = now + timedelta(days=3)
        notifications_created = 0

        # Find matters with deadlines in the next 3 days
        near_result = db.execute(
            select(Matter).where(
                Matter.status.in_(["pending", "in_progress"]),
                Matter.due_date.isnot(None),
                Matter.due_date >= now,
                Matter.due_date <= near_deadline,
            )
        ).scalars().all()

        for matter in near_result:
            days_left = 0
            if matter.due_date:
                days_left = (matter.due_date - now).days

            # Send to matter owner
            send_notification.delay(
                user_id=matter.owner_id,
                notification_type="due_warning",
                title=f"Matter due soon: {matter.title}",
                content=(
                    f"Matter '{matter.title}' ({matter.matter_no}) is due in approximately "
                    f"{days_left} day(s). Current progress: {matter.progress}%."
                ),
                matter_id=matter.id,
            )
            notifications_created += 1

            # 发送到期预警邮件给事项负责人
            try:
                owner_email = matter.owner.email if matter.owner else None
                if owner_email:
                    from app.utils.email_sender import email_sender as es
                    es.send_sync(
                        to_email=owner_email,
                        template_name="due_soon",
                        context={
                            "owner_name": matter.owner.real_name,
                            "matter_title": matter.title,
                            "due_date": matter.due_date.strftime("%Y-%m-%d") if matter.due_date else "N/A",
                            "days_remaining": days_left,
                        }
                    )
            except Exception:
                pass  # 邮件发送失败不影响主流程

        # Find overdue matters
        overdue_result = db.execute(
            select(Matter).where(
                Matter.status.in_(["pending", "in_progress"]),
                Matter.due_date.isnot(None),
                Matter.due_date < now,
            )
        ).scalars().all()

        for matter in overdue_result:
            days_overdue = 0
            if matter.due_date:
                days_overdue = (now - matter.due_date).days

            # Send to matter owner
            send_notification.delay(
                user_id=matter.owner_id,
                notification_type="overdue_alert",
                title=f"Matter OVERDUE: {matter.title}",
                content=(
                    f"Matter '{matter.title}' ({matter.matter_no}) is overdue by "
                    f"{days_overdue} day(s). Please take immediate action."
                ),
                matter_id=matter.id,
            )
            notifications_created += 1

            # 发送逾期提醒邮件给事项负责人
            try:
                owner_email = matter.owner.email if matter.owner else None
                if owner_email:
                    from app.utils.email_sender import email_sender as es
                    es.send_sync(
                        to_email=owner_email,
                        template_name="overdue",
                        context={
                            "owner_name": matter.owner.real_name,
                            "matter_title": matter.title,
                            "due_date": matter.due_date.strftime("%Y-%m-%d") if matter.due_date else "N/A",
                            "days_overdue": days_overdue,
                        }
                    )
            except Exception:
                pass  # 邮件发送失败不影响主流程

        return {
            "status": "SUCCESS",
            "near_deadline_count": len(
                [m for m in near_result if m.due_date and m.due_date >= now and m.due_date <= near_deadline]
            ) if near_result else 0,
            "overdue_count": len(overdue_result) if overdue_result else 0,
            "notifications_created": notifications_created,
        }

    except Exception as exc:
        return {
            "status": "FAILURE",
            "error": str(exc),
        }
    finally:
        db.close()


@celery_app.task
def check_sla_overdue():
    """
    Scan for workflow nodes whose SLA has expired.
    Marks overdue nodes and creates notifications.

    Intended to be called by Celery Beat on a regular schedule (e.g., every 4 hours).
    """
    from app.models.workflow import WorkflowNode

    db = next(get_sync_db())
    try:
        now = datetime.now(timezone.utc)
        notifications_created = 0

        # Find nodes where planned_finish_time has passed and sla_status is not already 'overdue'
        overdue_result = db.execute(
            select(WorkflowNode).where(
                WorkflowNode.planned_finish_time < now,
                WorkflowNode.sla_status != 'overdue',
                WorkflowNode.planned_finish_time.isnot(None),
                WorkflowNode.status.in_(["pending", "in_progress"]),
            )
        ).scalars().all()

        for node in overdue_result:
            node.sla_status = 'overdue'

            # Send notification to node owner
            send_notification.delay(
                user_id=node.owner_id,
                notification_type="sla_overdue",
                title=f"SLA timeout: {node.node_name}",
                content=(
                    f"Node '{node.node_name}' has exceeded its SLA deadline. "
                    f"Planned finish was: {node.planned_finish_time.isoformat() if node.planned_finish_time else 'N/A'}. "
                    f"Please take immediate action."
                ),
                matter_id=node.matter_id,
            )
            notifications_created += 1

            # 发送邮件通知给节点负责人
            try:
                owner_email = node.owner.email if node.owner else None
                if owner_email:
                    from app.utils.email_sender import email_sender as es
                    matter_title = node.matter.title if node.matter else ""
                    days_overdue = 0
                    if node.planned_finish_time:
                        days_overdue = (now - node.planned_finish_time).days
                    es.send_sync(
                        to_email=owner_email,
                        template_name="overdue",
                        context={
                            "owner_name": node.owner.real_name,
                            "matter_title": matter_title,
                            "due_date": node.planned_finish_time.strftime("%Y-%m-%d %H:%M") if node.planned_finish_time else "N/A",
                            "days_overdue": days_overdue,
                        }
                    )
            except Exception:
                pass  # 邮件发送失败不影响主流程

        # Also check for at-risk nodes (planned_finish_time within 2 hours)
        at_risk_threshold = now + timedelta(hours=2)
        at_risk_result = db.execute(
            select(WorkflowNode).where(
                WorkflowNode.planned_finish_time >= now,
                WorkflowNode.planned_finish_time <= at_risk_threshold,
                WorkflowNode.sla_status != 'at_risk',
                WorkflowNode.sla_status != 'overdue',
                WorkflowNode.planned_finish_time.isnot(None),
                WorkflowNode.status.in_(["pending", "in_progress"]),
            )
        ).scalars().all()

        for node in at_risk_result:
            node.sla_status = 'at_risk'

        db.commit()

        return {
            "status": "SUCCESS",
            "overdue_count": len(overdue_result) if overdue_result else 0,
            "at_risk_count": len(at_risk_result) if at_risk_result else 0,
            "notifications_created": notifications_created,
        }

    except Exception as exc:
        return {
            "status": "FAILURE",
            "error": str(exc),
        }
    finally:
        db.close()


@celery_app.task
def check_stalled_matters():
    """
    Check for matters with no progress in 7 days.
    Creates notifications for matter owners.

    Intended to be called by Celery Beat on a regular schedule (e.g., daily).
    """
    from app.models.matter import Matter

    db = next(get_sync_db())
    try:
        now = datetime.now(timezone.utc)
        stall_threshold = now - timedelta(days=7)
        notifications_created = 0

        # Find matters that are in progress but haven't been updated in 7 days
        stalled_result = db.execute(
            select(Matter).where(
                Matter.status.in_(["in_progress", "pending"]),
                Matter.updated_at <= stall_threshold,
                Matter.progress < 100,
            )
        ).scalars().all()

        for matter in stalled_result:
            days_since_update = 0
            if matter.updated_at:
                days_since_update = (now - matter.updated_at).days

            send_notification.delay(
                user_id=matter.owner_id,
                notification_type="stalled_alert",
                title=f"Matter stalled: {matter.title}",
                content=(
                    f"Matter '{matter.title}' ({matter.matter_no}) has not been updated "
                    f"in {days_since_update} days. Current progress: {matter.progress}%."
                ),
                matter_id=matter.id,
            )
            notifications_created += 1

        return {
            "status": "SUCCESS",
            "stalled_count": len(stalled_result) if stalled_result else 0,
            "notifications_created": notifications_created,
        }

    except Exception as exc:
        return {
            "status": "FAILURE",
            "error": str(exc),
        }
    finally:
        db.close()
