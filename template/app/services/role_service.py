from typing import List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories import (
    PrivilegeORM,
    PrivilegeRepository,
    RoleORM,
    RoleRepository,
    RoleSummary,
)


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.role_repo = RoleRepository(session)
        self.privilege_repo = PrivilegeRepository(session)

    async def list_roles(self, *, page: int, per_page: int) -> List[RoleSummary]:
        per_page = min(max(per_page, 1), 1000)
        page = max(page, 1)
        offset = (page - 1) * per_page
        return await self.role_repo.list_role_summaries(offset=offset, limit=per_page)

    async def count_roles(self, include_deleted: bool = False) -> int:
        return await self.role_repo.count_roles(include_deleted=include_deleted)

    async def create_role(
        self,
        name: str,
        privileges: Optional[Sequence[Tuple[str, str]]],
        is_superuser: bool = False,
    ) -> RoleORM:
        try:
            role = await self.role_repo.create(name=name, is_superuser=is_superuser)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if privileges:
            await self._sync_privileges(role, privileges)
        await self.session.commit()
        return await self.role_repo.get_by_id(role.id, include_deleted=False)  # type: ignore[arg-type]

    async def update_role(
        self,
        role_id: int,
        *,
        name: Optional[str] = None,
        privileges: Optional[Sequence[Tuple[str, str]]] = None,
        is_superuser: Optional[bool] = None,
    ) -> RoleORM:
        role = await self._require_role(role_id, include_deleted=False)
        try:
            updated_role = await self.role_repo.update_role(role, name=name, is_superuser=is_superuser)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if privileges is not None:
            updated_role.privileges.clear()
            await self.session.flush()
            await self._sync_privileges(updated_role, privileges)
        await self.session.commit()
        return await self.role_repo.get_by_id(updated_role.id, include_deleted=False)  # type: ignore[arg-type]

    async def delete_role(self, role_id: int, *, hard: bool = False) -> None:
        role = await self._require_role(role_id, include_deleted=True)
        if hard:
            await self.role_repo.hard_delete(role)
        else:
            await self.role_repo.soft_delete(role)
        await self.session.commit()

    async def restore_role(self, role_id: int) -> RoleORM:
        role = await self._require_role(role_id, include_deleted=True)
        if role.deleted_at is None:
            return role
        restored = await self.role_repo.restore(role)
        await self.session.commit()
        return restored

    async def get_role_by_name(self, name: str) -> Optional[RoleORM]:
        return await self.role_repo.get_by_name(name)

    async def get_role_detail(self, role_id: int) -> RoleORM:
        role = await self.role_repo.get_detailed_by_id(role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role

    async def _require_role(self, role_id: int, include_deleted: bool = False) -> RoleORM:
        role = await self.role_repo.get_by_id(role_id, include_deleted=include_deleted)
        if not role or (role.deleted_at and not include_deleted):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role

    async def _sync_privileges(
        self, role: RoleORM, privilege_specs: Sequence[Tuple[str, str]]
    ) -> None:
        for resource, action in privilege_specs:
            privilege = await self.privilege_repo.get_or_create(resource, action)
            await self.role_repo.attach_privilege(role, privilege)

    async def grant_privilege(self, role_id: int, resource: str, action: str) -> RoleORM:
        role = await self._require_role(role_id)
        privilege = await self.privilege_repo.get_or_create(resource, action)
        await self.role_repo.attach_privilege(role, privilege)
        await self.session.commit()
        return await self.role_repo.get_by_id(role_id)

    async def revoke_privilege(self, role_id: int, privilege_id: int) -> RoleORM:
        role = await self._require_role(role_id)
        privilege = await self.privilege_repo.get_by_id(privilege_id, include_deleted=False)
        if not privilege:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Privilege not found")
        await self.role_repo.detach_privilege(role, privilege)
        await self.session.commit()
        return await self.role_repo.get_by_id(role_id)
