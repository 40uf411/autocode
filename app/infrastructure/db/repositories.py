from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    and_,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.core.security import get_password_hash
from app.infrastructure.db.base import Base


@dataclass
class UserSummary:
    id: int
    email: str
    is_active: bool
    is_blocked: bool


@dataclass
class RoleSummary:
    id: int
    name: str
    is_superuser: bool


@dataclass
class RolePrivilegeLink:
    role_id: int
    privilege_id: int
    role_name: str
    privilege_resource: str
    privilege_action: str
    privilege_description: Optional[str]

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Index("ix_user_roles_user_id", "user_id"),
    Index("ix_user_roles_role_id", "role_id"),
)

role_privileges = Table(
    "role_privileges",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("privilege_id", ForeignKey("privileges.id"), primary_key=True),
    Index("ix_role_privileges_role_id", "role_id"),
    Index("ix_role_privileges_privilege_id", "privilege_id"),
)


class PrivilegeORM(Base):
    __tablename__ = "privileges"
    __editable__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_privilege_resource_action"),
        Index("ix_privilege_resource", "resource"),
        Index("ix_privilege_action", "action"),
        Index("ix_privilege_deleted", "deleted_at"),
        Index("ix_privilege_deleted_id", "deleted_at", "id"),
    )

class RoleORM(Base):
    __tablename__ = "roles"
    __editable__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    privileges: Mapped[List[PrivilegeORM]] = relationship(
        "PrivilegeORM",
        secondary=role_privileges,
        lazy="selectin",
        backref="roles",
    )

    __table_args__ = (
        Index("ix_roles_name_idx", "name"),
        Index("ix_roles_deleted_idx", "deleted_at"),
        Index("ix_roles_superuser_idx", "is_superuser"),
        Index("ix_roles_deleted_id", "deleted_at", "id"),
    )


class UserORM(Base):
    __tablename__ = "users"
    __editable__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    roles: Mapped[List[RoleORM]] = relationship(
        "RoleORM",
        secondary=user_roles,
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_blocked", "is_blocked"),
        Index("ix_users_deleted", "deleted_at"),
        Index("ix_users_deleted_id", "deleted_at", "id"),
    )


class ActivityLogORM(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_context: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_activity_logs_user_id", "user_id"),
        Index("ix_activity_logs_path", "path"),
    )


class PrivilegeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self, privilege_id: int, include_deleted: bool = False
    ) -> Optional[PrivilegeORM]:
        stmt = select(PrivilegeORM).where(PrivilegeORM.id == privilege_id)
        if not include_deleted:
            stmt = stmt.where(PrivilegeORM.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self, resource: str, action: str, description: Optional[str] = None
    ) -> PrivilegeORM:
        stmt = select(PrivilegeORM).where(
            PrivilegeORM.resource == resource,
            PrivilegeORM.action == action,
            PrivilegeORM.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        privilege = result.scalar_one_or_none()
        if privilege:
            return privilege
        privilege = PrivilegeORM(resource=resource, action=action, description=description)
        self.session.add(privilege)
        await self.session.flush()
        return privilege

    async def list(
        self, include_deleted: bool = False, *, offset: int = 0, limit: int = 100
    ) -> List[PrivilegeORM]:
        stmt = select(PrivilegeORM).offset(offset).limit(limit).order_by(PrivilegeORM.id)
        if not include_deleted:
            stmt = stmt.where(PrivilegeORM.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, include_deleted: bool = False) -> int:
        stmt = select(func.count(PrivilegeORM.id))
        if not include_deleted:
            stmt = stmt.where(PrivilegeORM.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(
        self,
        privilege: PrivilegeORM,
        *,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PrivilegeORM:
        if resource:
            privilege.resource = resource
        if action:
            privilege.action = action
        if description is not None:
            privilege.description = description
        await self.session.flush()
        return privilege

    async def soft_delete(self, privilege: PrivilegeORM) -> None:
        privilege.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def hard_delete(self, privilege: PrivilegeORM) -> None:
        await self.session.delete(privilege)

    async def restore(self, privilege: PrivilegeORM) -> PrivilegeORM:
        privilege.deleted_at = None
        await self.session.flush()
        return privilege


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, name: str) -> Optional[RoleORM]:
        stmt = (
            select(RoleORM)
            .options(selectinload(RoleORM.privileges))
            .where(RoleORM.name == name, RoleORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, role_id: int, include_deleted: bool = False) -> Optional[RoleORM]:
        stmt = select(RoleORM).options(selectinload(RoleORM.privileges)).where(RoleORM.id == role_id)
        if not include_deleted:
            stmt = stmt.where(RoleORM.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        privilege_ids: Optional[List[int]] = None,
        is_superuser: bool = False,
    ) -> RoleORM:
        if is_superuser:
            await self._assert_single_super_role()
        role = RoleORM(name=name, is_superuser=is_superuser)
        if privilege_ids:
            stmt = (
                select(PrivilegeORM)
                .where(PrivilegeORM.id.in_(privilege_ids), PrivilegeORM.deleted_at.is_(None))
            )
            privileges = (await self.session.scalars(stmt)).all()
            role.privileges = list(privileges)
        self.session.add(role)
        await self.session.flush()
        return role

    async def attach_privilege(self, role: RoleORM, privilege: PrivilegeORM) -> None:
        if not role.id or not privilege.id:
            return
        stmt = select(role_privileges.c.role_id).where(
            role_privileges.c.role_id == role.id,
            role_privileges.c.privilege_id == privilege.id,
        )
        if (await self.session.execute(stmt)).first():
            return
        await self.session.execute(
            role_privileges.insert().values(role_id=role.id, privilege_id=privilege.id)
        )
        await self.session.flush()

    async def detach_privilege(self, role: RoleORM, privilege: PrivilegeORM) -> None:
        if not role.id or not privilege.id:
            return
        await self.session.execute(
            role_privileges.delete().where(
                role_privileges.c.role_id == role.id,
                role_privileges.c.privilege_id == privilege.id,
            )
        )
        await self.session.flush()

    async def list_role_summaries(
        self, include_deleted: bool = False, *, offset: int = 0, limit: int = 100
    ) -> List[RoleSummary]:
        stmt = (
            select(RoleORM.id, RoleORM.name, RoleORM.is_superuser)
            .offset(offset)
            .limit(limit)
            .order_by(RoleORM.id)
        )
        if not include_deleted:
            stmt = stmt.where(RoleORM.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return [RoleSummary(*row) for row in result.all()]

    async def count_roles(self, include_deleted: bool = False) -> int:
        stmt = select(func.count(RoleORM.id))
        if not include_deleted:
            stmt = stmt.where(RoleORM.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_detailed_by_id(self, role_id: int) -> Optional[RoleORM]:
        stmt = (
            select(RoleORM)
            .options(selectinload(RoleORM.privileges))
            .where(RoleORM.id == role_id, RoleORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_role(
        self,
        role: RoleORM,
        name: Optional[str] = None,
        is_superuser: Optional[bool] = None,
    ) -> RoleORM:
        if name:
            role.name = name
        if is_superuser is not None and is_superuser != role.is_superuser:
            if is_superuser:
                await self._assert_single_super_role(exclude_role_id=role.id)
            role.is_superuser = is_superuser
        await self.session.flush()
        return role

    async def soft_delete(self, role: RoleORM) -> None:
        role.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def hard_delete(self, role: RoleORM) -> None:
        await self.session.delete(role)

    async def restore(self, role: RoleORM) -> RoleORM:
        role.deleted_at = None
        await self.session.flush()
        return role

    async def get_super_role(self) -> Optional[RoleORM]:
        stmt = select(RoleORM).where(RoleORM.is_superuser.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _assert_single_super_role(self, exclude_role_id: Optional[int] = None) -> None:
        stmt = select(RoleORM).where(RoleORM.is_superuser.is_(True))
        if exclude_role_id is not None:
            stmt = stmt.where(RoleORM.id != exclude_role_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("A superuser role already exists")


class RolePrivilegeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_links(self, *, offset: int = 0, limit: int = 100) -> List[RolePrivilegeLink]:
        stmt = (
            select(
                role_privileges.c.role_id.label("role_id"),
                role_privileges.c.privilege_id.label("privilege_id"),
                RoleORM.name.label("role_name"),
                PrivilegeORM.resource.label("privilege_resource"),
                PrivilegeORM.action.label("privilege_action"),
                PrivilegeORM.description.label("privilege_description"),
            )
            .select_from(role_privileges)
            .join(RoleORM, RoleORM.id == role_privileges.c.role_id)
            .join(PrivilegeORM, PrivilegeORM.id == role_privileges.c.privilege_id)
            .order_by(role_privileges.c.role_id, role_privileges.c.privilege_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [
            RolePrivilegeLink(
                role_id=row.role_id,
                privilege_id=row.privilege_id,
                role_name=row.role_name,
                privilege_resource=row.privilege_resource,
                privilege_action=row.privilege_action,
                privilege_description=row.privilege_description,
            )
            for row in result.all()
        ]

    async def count_links(self) -> int:
        stmt = select(func.count()).select_from(role_privileges)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_link(self, role_id: int, privilege_id: int) -> Optional[RolePrivilegeLink]:
        stmt = (
            select(
                role_privileges.c.role_id.label("role_id"),
                role_privileges.c.privilege_id.label("privilege_id"),
                RoleORM.name.label("role_name"),
                PrivilegeORM.resource.label("privilege_resource"),
                PrivilegeORM.action.label("privilege_action"),
                PrivilegeORM.description.label("privilege_description"),
            )
            .select_from(role_privileges)
            .join(RoleORM, RoleORM.id == role_privileges.c.role_id)
            .join(PrivilegeORM, PrivilegeORM.id == role_privileges.c.privilege_id)
            .where(
                role_privileges.c.role_id == role_id,
                role_privileges.c.privilege_id == privilege_id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return None
        return RolePrivilegeLink(
            role_id=row.role_id,
            privilege_id=row.privilege_id,
            role_name=row.role_name,
            privilege_resource=row.privilege_resource,
            privilege_action=row.privilege_action,
            privilege_description=row.privilege_description,
        )

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_user_summaries(self, *, offset: int = 0, limit: int = 100) -> List[UserSummary]:
        stmt = (
            select(UserORM.id, UserORM.email, UserORM.is_active, UserORM.is_blocked)
            .where(UserORM.deleted_at.is_(None))
            .order_by(UserORM.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [UserSummary(*row) for row in result.all()]

    async def count_users(self) -> int:
        stmt = select(func.count(UserORM.id)).where(UserORM.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_email(self, email: str) -> Optional[UserORM]:
        stmt = (
            select(UserORM)
            .where(UserORM.email == email, UserORM.deleted_at.is_(None))
            .options(selectinload(UserORM.roles).selectinload(RoleORM.privileges))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[UserORM]:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id, UserORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_include_deleted(self, user_id: int) -> Optional[UserORM]:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .options(selectinload(UserORM.roles).selectinload(RoleORM.privileges))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password: str,
        is_blocked: bool = False,
        role_ids: Optional[List[int]] = None,
    ) -> UserORM:
        user = UserORM(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_blocked=is_blocked,
        )
        if role_ids:
            stmt = select(RoleORM).where(RoleORM.id.in_(role_ids))
            roles = (await self.session.scalars(stmt)).all()
            user.roles = list(roles)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_detailed_by_id(self, user_id: int) -> Optional[UserORM]:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id, UserORM.deleted_at.is_(None))
            .options(selectinload(UserORM.roles).selectinload(RoleORM.privileges))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def attach_roles(self, user: UserORM, role_ids: List[int]) -> None:
        stmt = select(RoleORM).where(RoleORM.id.in_(role_ids), RoleORM.deleted_at.is_(None))
        roles = (await self.session.scalars(stmt)).all()
        for role in roles:
            if role not in user.roles:
                user.roles.append(role)
        await self.session.flush()

    async def detach_roles(self, user: UserORM, role_ids: List[int]) -> None:
        user.roles = [role for role in user.roles if role.id not in role_ids]
        await self.session.flush()

    async def update_user(
        self,
        user: UserORM,
        *,
        email: Optional[str] = None,
        role_ids: Optional[List[int]] = None,
    ) -> UserORM:
        if email:
            user.email = email
        if role_ids is not None:
            stmt = select(RoleORM).where(RoleORM.id.in_(role_ids), RoleORM.deleted_at.is_(None))
            roles = (await self.session.scalars(stmt)).all()
            user.roles = list(roles)
        await self.session.flush()
        return user

    async def set_block_status(self, user: UserORM, blocked: bool) -> UserORM:
        user.is_blocked = blocked
        await self.session.flush()
        return user

    async def reset_password(self, user: UserORM, password: str) -> UserORM:
        user.hashed_password = get_password_hash(password)
        await self.session.flush()
        return user

    async def soft_delete(self, user: UserORM) -> None:
        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        await self.session.flush()

    async def restore(self, user: UserORM) -> UserORM:
        user.deleted_at = None
        user.is_active = True
        await self.session.flush()
        return user

    async def hard_delete(self, user: UserORM) -> None:
        await self.session.delete(user)

    async def user_has_privilege(self, user_id: int, resource: str, action: str) -> bool:
        stmt = (
            select(func.count(PrivilegeORM.id))
            .select_from(UserORM)
            .join(user_roles, UserORM.id == user_roles.c.user_id)
            .join(RoleORM, RoleORM.id == user_roles.c.role_id)
            .join(role_privileges, RoleORM.id == role_privileges.c.role_id)
            .join(PrivilegeORM, PrivilegeORM.id == role_privileges.c.privilege_id)
            .where(
                and_(
                    UserORM.id == user_id,
                    UserORM.deleted_at.is_(None),
                    RoleORM.deleted_at.is_(None),
                    PrivilegeORM.deleted_at.is_(None),
                    PrivilegeORM.resource == resource,
                    PrivilegeORM.action == action,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def user_is_superuser(self, user_id: int) -> bool:
        stmt = (
            select(func.count(RoleORM.id))
            .select_from(UserORM)
            .join(user_roles, UserORM.id == user_roles.c.user_id)
            .join(RoleORM, RoleORM.id == user_roles.c.role_id)
            .where(UserORM.id == user_id, RoleORM.is_superuser.is_(True), RoleORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0


class ActivityLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_log(
        self,
        *,
        user_id: Optional[int],
        method: str,
        path: str,
        status_code: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
        client_context: Optional[str],
    ) -> None:
        log = ActivityLogORM(
            user_id=user_id,
            method=method[:10],
            path=path[:255],
            status_code=status_code,
            ip_address=ip_address[:64] if ip_address else None,
            user_agent=user_agent[:255] if user_agent else None,
            client_context=client_context[:255] if client_context else None,
        )
        self.session.add(log)
