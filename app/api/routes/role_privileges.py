from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_role_privilege_service, require_superuser
from app.api.schemas import RolePrivilegeLinkCreateSchema, RolePrivilegeLinkSchema
from app.services.role_privilege_service import RolePrivilegeService

router = APIRouter(
    prefix="/role_privileges",
    tags=["role_privileges"],
    dependencies=[Depends(require_superuser)],
)


@router.get("/", response_model=List[RolePrivilegeLinkSchema])
async def list_role_privileges(
    page: int = 1,
    per_page: int = 50,
    service: RolePrivilegeService = Depends(get_role_privilege_service),
) -> List[RolePrivilegeLinkSchema]:
    return await service.list_links(page=page, per_page=per_page)


@router.get("/count")
async def count_role_privileges(
    service: RolePrivilegeService = Depends(get_role_privilege_service),
) -> dict[str, int]:
    return {"count": await service.count_links()}


@router.get("/{role_id}/{privilege_id}", response_model=RolePrivilegeLinkSchema)
async def get_role_privilege(
    role_id: UUID,
    privilege_id: UUID,
    service: RolePrivilegeService = Depends(get_role_privilege_service),
) -> RolePrivilegeLinkSchema:
    return await service.get_link(role_id, privilege_id)


@router.post(
    "/",
    response_model=RolePrivilegeLinkSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_privilege(
    payload: RolePrivilegeLinkCreateSchema,
    service: RolePrivilegeService = Depends(get_role_privilege_service),
) -> RolePrivilegeLinkSchema:
    return await service.create_link(payload.role_id, payload.privilege_id)


@router.delete(
    "/{role_id}/{privilege_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role_privilege(
    role_id: UUID,
    privilege_id: UUID,
    service: RolePrivilegeService = Depends(get_role_privilege_service),
) -> None:
    await service.delete_link(role_id, privilege_id)
