from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories import (
    PrivilegeRepository,
    RolePrivilegeLink,
    RolePrivilegeRepository,
    RoleRepository,
)


class RolePrivilegeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.role_repo = RoleRepository(session)
        self.privilege_repo = PrivilegeRepository(session)
        self.link_repo = RolePrivilegeRepository(session)

    async def list_links(self, *, page: int, per_page: int) -> List[RolePrivilegeLink]:
        per_page = min(max(per_page, 1), 1000)
        page = max(page, 1)
        offset = (page - 1) * per_page
        return await self.link_repo.list_links(offset=offset, limit=per_page)

    async def count_links(self) -> int:
        return await self.link_repo.count_links()

    async def get_link(self, role_id: int, privilege_id: int) -> RolePrivilegeLink:
        link = await self.link_repo.get_link(role_id, privilege_id)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role-privilege relation not found",
            )
        return link

    async def create_link(self, role_id: int, privilege_id: int) -> RolePrivilegeLink:
        role = await self.role_repo.get_by_id(role_id)
        if not role or role.deleted_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        privilege = await self.privilege_repo.get_by_id(privilege_id)
        if not privilege or privilege.deleted_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Privilege not found")
        await self.role_repo.attach_privilege(role, privilege)
        await self.session.commit()
        return await self.get_link(role_id, privilege_id)

    async def delete_link(self, role_id: int, privilege_id: int) -> None:
        link = await self.link_repo.get_link(role_id, privilege_id)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role-privilege relation not found",
            )
        role = await self.role_repo.get_by_id(role_id)
        privilege = await self.privilege_repo.get_by_id(privilege_id)
        if not role or role.deleted_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if not privilege or privilege.deleted_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Privilege not found")
        await self.role_repo.detach_privilege(role, privilege)
        await self.session.commit()
