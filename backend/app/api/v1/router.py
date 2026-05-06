from fastapi import APIRouter
from app.api.v1 import (
    auth, users, documents, notifications, audit,
    webhooks, ws, ai, task_templates, task_instances, system,
    tasks, dashboard, search, public_dashboard,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(task_templates.router, prefix="/task-templates", tags=["Task Templates"])
api_router.include_router(task_instances.router, prefix="/task-instances", tags=["Task Instances"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["Audit"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(system.router, prefix="/system", tags=["System"])
api_router.include_router(ws.router, tags=["WebSocket"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Assistant"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(public_dashboard.router, tags=["Public Dashboard"])
