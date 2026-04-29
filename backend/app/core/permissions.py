from enum import Enum
from typing import Optional


class RoleCode(str, Enum):
    GENERAL_STAFF = "general_staff"
    MATTER_OWNER = "matter_owner"
    DEPT_LEADER = "dept_leader"
    ADMIN = "admin"


class Permission(str, Enum):
    # Document permissions
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_EDIT = "document:edit"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_DOWNLOAD = "document:download"
    DOCUMENT_LOCK = "document:lock"
    DOCUMENT_SET_OFFICIAL = "document:set_official"

    # Matter permissions
    MATTER_VIEW = "matter:view"
    MATTER_CREATE = "matter:create"
    MATTER_EDIT = "matter:edit"
    MATTER_DELETE = "matter:delete"
    MATTER_MANAGE_MEMBERS = "matter:manage_members"
    MATTER_ADVANCE_NODE = "matter:advance_node"

    # Workflow permissions
    WORKFLOW_TEMPLATE_MANAGE = "workflow:template_manage"

    # Admin permissions
    ADMIN_USER_MANAGE = "admin:user_manage"
    ADMIN_ROLE_MANAGE = "admin:role_manage"
    ADMIN_AUDIT_VIEW = "admin:audit_view"

    # Dashboard
    DASHBOARD_VIEW = "dashboard:view"


ROLE_PERMISSIONS: dict[RoleCode, list[Permission]] = {
    RoleCode.GENERAL_STAFF: [
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.MATTER_VIEW,
    ],
    RoleCode.MATTER_OWNER: [
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_EDIT,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.DOCUMENT_LOCK,
        Permission.DOCUMENT_SET_OFFICIAL,
        Permission.MATTER_VIEW,
        Permission.MATTER_CREATE,
        Permission.MATTER_EDIT,
        Permission.MATTER_MANAGE_MEMBERS,
        Permission.MATTER_ADVANCE_NODE,
    ],
    RoleCode.DEPT_LEADER: [
        Permission.DOCUMENT_VIEW,
        Permission.DOCUMENT_UPLOAD,
        Permission.DOCUMENT_EDIT,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.DOCUMENT_LOCK,
        Permission.DOCUMENT_SET_OFFICIAL,
        Permission.MATTER_VIEW,
        Permission.MATTER_CREATE,
        Permission.MATTER_EDIT,
        Permission.MATTER_DELETE,
        Permission.MATTER_MANAGE_MEMBERS,
        Permission.MATTER_ADVANCE_NODE,
        Permission.WORKFLOW_TEMPLATE_MANAGE,
        Permission.DASHBOARD_VIEW,
        Permission.ADMIN_AUDIT_VIEW,
    ],
    RoleCode.ADMIN: [
        p for p in Permission
    ],
}


def get_permissions_for_role(role_code: RoleCode) -> list[Permission]:
    return ROLE_PERMISSIONS.get(role_code, [])


def has_permission(role_code: RoleCode, permission: Permission) -> bool:
    return permission in get_permissions_for_role(role_code)
