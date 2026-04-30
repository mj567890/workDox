from sqlalchemy import String, ForeignKey, Column, Integer, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("role.id"), primary_key=True),
)


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("department.id"))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, disabled
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")  # local, ldap, oauth2
    oauth_provider: Mapped[str | None] = mapped_column(String(50))  # oidc, generic
    oauth_subject: Mapped[str | None] = mapped_column(String(200), unique=True)  # OAuth2/OIDC sub claim

    department = relationship("Department", back_populates="users")
    roles: Mapped[list["Role"]] = relationship("Role", secondary=user_role, back_populates="users")
