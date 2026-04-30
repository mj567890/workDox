import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.config import get_settings
from app.models.base import Base

# Import all models to ensure they're registered
from app.models.department import Department
from app.models.user import User
from app.models.role import Role
from app.models.document import Document, DocumentVersion, DocumentTag, DocumentEditLock, DocumentCategory, Tag
from app.models.notification import Notification
from app.models.operation_log import OperationLog
from app.models.system_config import SystemConfig
from app.models.ai_provider import AIProvider
from app.models.task_manager import TaskTemplate, StageTemplate, SlotTemplate, ProjectTask, ProjectStage, ProjectSlot, SlotVersion

settings = get_settings()
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
