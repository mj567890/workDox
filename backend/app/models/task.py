"""Task model — ProjectTask from task_manager (new task system)."""

from app.models.task_manager import ProjectTask as Task

# The old "task" table was dropped via remove_legacy_matter_workflow migration.
# The new task system uses task_instance table (ProjectTask).
