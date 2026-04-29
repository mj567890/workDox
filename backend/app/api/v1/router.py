from fastapi import APIRouter
from app.api.v1 import auth, users, documents, matters, workflow_templates, workflow_nodes, tasks, notifications, search, dashboard, audit, webhooks, ws, public_dashboard, ai

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(matters.router, prefix="/matters", tags=["Matters"])
api_router.include_router(workflow_templates.router, prefix="/workflow", tags=["Workflow"])
api_router.include_router(workflow_nodes.router, tags=["Workflow Nodes"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["Audit"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(ws.router, tags=["WebSocket"])
api_router.include_router(public_dashboard.router, tags=["Public Dashboard"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Assistant"])
