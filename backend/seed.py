"""Seed initial data for ODMS development/testing."""
import sys
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core.security import hash_password
from app.models.base import Base
from app.models.department import Department
from app.models.user import User, user_role
from app.models.role import Role
from app.models.document import DocumentCategory, Tag
from app.models.notification import Notification

settings = get_settings()
engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)


def seed():
    with Session(engine) as db:
        # Check if already seeded
        existing = db.execute(select(Role).limit(1)).scalar_one_or_none()
        if existing:
            print("Database already seeded. Skipping.")
            return

        # ── Roles ──
        roles = [
            Role(role_name="普通员工", role_code="general_staff", description="基本用户角色"),
            Role(role_name="事项负责人", role_code="matter_owner", description="业务事项负责人"),
            Role(role_name="部门领导", role_code="dept_leader", description="部门领导"),
            Role(role_name="系统管理员", role_code="admin", description="系统管理员"),
        ]
        db.add_all(roles)
        db.flush()

        # ── Department ──
        dept = Department(name="综合办公室", code="office")
        db.add(dept)
        db.flush()

        # ── Users ──
        admin_user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            real_name="系统管理员",
            email="admin@odms.local",
            department_id=dept.id,
            status="active",
        )
        staff_user = User(
            username="zhangsan",
            password_hash=hash_password("zhangsan123"),
            real_name="张三",
            email="zhangsan@odms.local",
            department_id=dept.id,
            status="active",
        )
        leader_user = User(
            username="lisi",
            password_hash=hash_password("lisi123"),
            real_name="李四",
            email="lisi@odms.local",
            department_id=dept.id,
            status="active",
        )
        db.add_all([admin_user, staff_user, leader_user])
        db.flush()

        # Assign roles: admin -> admin, zhangsan -> matter_owner + general_staff, lisi -> dept_leader + general_staff
        db.execute(
            user_role.insert().values([
                {"user_id": admin_user.id, "role_id": roles[3].id},
                {"user_id": staff_user.id, "role_id": roles[0].id},
                {"user_id": staff_user.id, "role_id": roles[1].id},
                {"user_id": leader_user.id, "role_id": roles[0].id},
                {"user_id": leader_user.id, "role_id": roles[2].id},
            ])
        )

        # ── Document Categories ──
        doc_categories = [
            DocumentCategory(name="通知文件", code="notice", sort_order=1, is_system=True),
            DocumentCategory(name="方案材料", code="plan_material", sort_order=2, is_system=True),
            DocumentCategory(name="报审材料", code="approval_material", sort_order=3, is_system=True),
            DocumentCategory(name="签批文件", code="signed_doc", sort_order=4, is_system=True),
            DocumentCategory(name="会议纪要", code="meeting_notes", sort_order=5, is_system=True),
            DocumentCategory(name="其他材料", code="other", sort_order=99, is_system=True),
        ]
        db.add_all(doc_categories)
        db.flush()

        # ── Tags ──
        tags = [
            Tag(name="紧急", color="#F56C6C"),
            Tag(name="重要", color="#E6A23C"),
            Tag(name="已签批", color="#67C23A"),
            Tag(name="待审核", color="#409EFF"),
            Tag(name="机密", color="#909399"),
        ]
        db.add_all(tags)
        db.flush()

        # ── Sample Notification ──
        notif = Notification(
            user_id=leader_user.id,
            type="system",
            title="欢迎使用 WorkDox",
            content="系统已初始化完成，开始使用吧！",
        )
        db.add(notif)

        db.commit()
        print("Seed data created successfully!")
        print()
        print("Test accounts:")
        print("  admin    / admin123     (系统管理员)")
        print("  zhangsan / zhangsan123  (事项负责人)")
        print("  lisi     / lisi123      (部门领导)")


if __name__ == "__main__":
    seed()
