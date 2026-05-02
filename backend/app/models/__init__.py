from app.models.base import Base, TimestampMixin
from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.document import (
    DocumentCategory, Tag, Document, DocumentVersion,
    DocumentEditLock, DocumentReview,
)
from app.models.task import Task
from app.models.notification import Notification
from app.models.operation_log import OperationLog
from app.models.webhook import WebhookSubscription
from app.models.ai import DocumentChunk, AIConversation, AIMessage
from app.models.ai_provider import AIProvider
from app.models.system_config import SystemConfig
from app.models.task_manager import (
    TaskTemplate, StageTemplate, SlotTemplate,
    ProjectStage, ProjectSlot, SlotVersion,
)
# Note: ProjectTask is re-exported as Task by app.models.task
