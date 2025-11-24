from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories import PrivilegeORM, PrivilegeRepository


class PrivilegeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PrivilegeRepository(session)

    async def list_privileges(
        self,
        include_deleted: bool = False,
        *,
        page: int,
        per_page: int,
    ) -> List[PrivilegeORM]:
        per_page = min(max(per_page, 1), 1000)
        page = max(page, 1)
        offset = (page - 1) * per_page
        return await self.repo.list(include_deleted=include_deleted, offset=offset, limit=per_page)

    async def count(self, include_deleted: bool = False) -> int:
        return await self.repo.count(include_deleted=include_deleted)

    async def create_privilege(self, resource: str, action: str, description: Optional[str]) -> PrivilegeORM:
        existing = await self.repo.get_or_create(resource, action, description)
        if existing.deleted_at:
            restored = await self.repo.restore(existing)
            await self.session.commit()
            return restored
        await self.session.commit()
        return existing

    async def update_privilege(
        self,
        privilege_id: UUID,
        *,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PrivilegeORM:
        privilege = await self._require_privilege(privilege_id)
        updated = await self.repo.update(
            privilege, resource=resource, action=action, description=description
        )
        await self.session.commit()
        return updated

    async def delete_privilege(self, privilege_id: UUID, *, hard: bool = False) -> None:
        privilege = await self._require_privilege(privilege_id, include_deleted=True)
        if hard:
            await self.repo.hard_delete(privilege)
        else:
            await self.repo.soft_delete(privilege)
        await self.session.commit()

    async def restore_privilege(self, privilege_id: UUID) -> PrivilegeORM:
        privilege = await self._require_privilege(privilege_id, include_deleted=True)
        if privilege.deleted_at is None:
            return privilege
        restored = await self.repo.restore(privilege)
        await self.session.commit()
        return restored

    async def _require_privilege(
        self, privilege_id: UUID, include_deleted: bool = False
    ) -> PrivilegeORM:
        privilege = await self.repo.get_by_id(privilege_id, include_deleted=include_deleted)
        if not privilege or (privilege.deleted_at and not include_deleted):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Privilege not found")
        return privilege
