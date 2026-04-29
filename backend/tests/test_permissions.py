"""Tests for RBAC permission system."""

import pytest
from app.core.permissions import (
    RoleCode,
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_role,
    has_permission,
)


class TestPermissionDefinitions:
    def test_all_roles_have_permissions(self):
        for role in RoleCode:
            assert role in ROLE_PERMISSIONS, f"{role} missing permissions"

    def test_admin_has_all_permissions(self):
        admin_perms = get_permissions_for_role(RoleCode.ADMIN)
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing {perm}"

    def test_general_staff_limited_permissions(self):
        perms = get_permissions_for_role(RoleCode.GENERAL_STAFF)
        # Can view and upload but not delete
        assert Permission.DOCUMENT_VIEW in perms
        assert Permission.DOCUMENT_UPLOAD in perms
        assert Permission.DOCUMENT_DELETE not in perms

    def test_matter_owner_permissions(self):
        perms = get_permissions_for_role(RoleCode.MATTER_OWNER)
        # Can manage matters but not users
        assert Permission.MATTER_CREATE in perms
        assert Permission.MATTER_ADVANCE_NODE in perms
        assert Permission.ADMIN_USER_MANAGE not in perms

    def test_dept_leader_permissions(self):
        perms = get_permissions_for_role(RoleCode.DEPT_LEADER)
        assert Permission.DASHBOARD_VIEW in perms
        assert Permission.WORKFLOW_TEMPLATE_MANAGE in perms
        assert Permission.ADMIN_AUDIT_VIEW in perms
        assert Permission.ADMIN_USER_MANAGE not in perms


class TestPermissionCheck:
    def test_admin_can_do_anything(self):
        for perm in Permission:
            assert has_permission(RoleCode.ADMIN, perm) is True

    def test_staff_can_view_document(self):
        assert has_permission(
            RoleCode.GENERAL_STAFF, Permission.DOCUMENT_VIEW
        ) is True

    def test_staff_cannot_delete_document(self):
        assert has_permission(
            RoleCode.GENERAL_STAFF, Permission.DOCUMENT_DELETE
        ) is False

    def test_staff_cannot_manage_users(self):
        assert has_permission(
            RoleCode.GENERAL_STAFF, Permission.ADMIN_USER_MANAGE
        ) is False

    @pytest.mark.parametrize("role,perm_name,expected", [
        (RoleCode.GENERAL_STAFF, "document:view", True),
        (RoleCode.GENERAL_STAFF, "document:delete", False),
        (RoleCode.MATTER_OWNER, "matter:create", True),
        (RoleCode.MATTER_OWNER, "admin:user_manage", False),
        (RoleCode.DEPT_LEADER, "dashboard:view", True),
        (RoleCode.DEPT_LEADER, "admin:audit_view", True),
        (RoleCode.ADMIN, "admin:user_manage", True),
        (RoleCode.ADMIN, "workflow:template_manage", True),
    ])
    def test_permission_matrix(self, role, perm_name, expected):
        perm = Permission(perm_name)
        assert has_permission(role, perm) == expected


class TestRoleCodeEnum:
    def test_role_code_values(self):
        assert RoleCode.GENERAL_STAFF == "general_staff"
        assert RoleCode.MATTER_OWNER == "matter_owner"
        assert RoleCode.DEPT_LEADER == "dept_leader"
        assert RoleCode.ADMIN == "admin"

    def test_parse_from_string(self):
        assert RoleCode("admin") == RoleCode.ADMIN
        assert RoleCode("general_staff") == RoleCode.GENERAL_STAFF
        with pytest.raises(ValueError):
            RoleCode("invalid_role")
