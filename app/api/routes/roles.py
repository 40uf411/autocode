from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_role_service, require_privilege
from app.api.schemas import (
    PrivilegeSchema,
    RoleCreateSchema,
    RoleSchema,
    RoleSummarySchema,
    RoleUpdateSchema,
)
from app.infrastructure.db.repositories import RoleORM
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "/",
    response_model=List[RoleSummarySchema],
    dependencies=[Depends(require_privilege("roles", "read"))],
)
async def list_roles(
    page: int = 1,
    per_page: int = 50,
    role_service: RoleService = Depends(get_role_service),
) -> List[RoleSummarySchema]:
    return await role_service.list_roles(page=page, per_page=per_page)


@router.post(
    "/",
    response_model=RoleSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_privilege("roles", "insert"))],
)
async def create_role(
    payload: RoleCreateSchema,
    role_service: RoleService = Depends(get_role_service),
) -> RoleORM:
    privileges = None
    if payload.privileges:
        privileges = [(p.resource, p.action) for p in payload.privileges]
    role = await role_service.create_role(payload.name, privileges, is_superuser=payload.is_superuser)
    return role


@router.post(
    "/{role_id}/privileges",
    response_model=RoleSchema,
    dependencies=[Depends(require_privilege("roles", "update"))],
)
async def grant_privilege_to_role(
    role_id: UUID,
    payload: PrivilegeSchema,
    role_service: RoleService = Depends(get_role_service),
) -> RoleORM:
    return await role_service.grant_privilege(role_id, payload.resource, payload.action)


@router.delete(
    "/{role_id}/privileges/{privilege_id}",
    response_model=RoleSchema,
    dependencies=[Depends(require_privilege("roles", "update"))],
)
async def revoke_privilege_from_role(
    role_id: UUID,
    privilege_id: UUID,
    role_service: RoleService = Depends(get_role_service),
) -> RoleORM:
    return await role_service.revoke_privilege(role_id, privilege_id)


@router.get(
    "/count",
    dependencies=[Depends(require_privilege("roles", "read"))],
)
async def count_roles(
    include_deleted: bool = False,
    role_service: RoleService = Depends(get_role_service),
) -> dict[str, int]:
    return {"count": await role_service.count_roles(include_deleted=include_deleted)}


@router.get(
    "/{role_id}",
    response_model=RoleSchema,
    dependencies=[Depends(require_privilege("roles", "read"))],
)
async def get_role_detail(role_id: UUID, role_service: RoleService = Depends(get_role_service)) -> RoleORM:
    return await role_service.get_role_detail(role_id)


@router.patch(
    "/{role_id}",
    response_model=RoleSchema,
    dependencies=[Depends(require_privilege("roles", "update"))],
)
async def update_role(
    role_id: UUID,
    payload: RoleUpdateSchema,
    role_service: RoleService = Depends(get_role_service),
) -> RoleORM:
    privilege_specs = None
    if payload.privileges is not None:
        privilege_specs = [(p.resource, p.action) for p in payload.privileges]
    return await role_service.update_role(
        role_id,
        name=payload.name,
        privileges=privilege_specs,
        is_superuser=payload.is_superuser,
    )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_privilege("roles", "delete"))],
)
async def delete_role(
    role_id: UUID,
    hard: bool = False,
    role_service: RoleService = Depends(get_role_service),
) -> None:
    await role_service.delete_role(role_id, hard=hard)


@router.post(
    "/{role_id}/restore",
    response_model=RoleSchema,
    dependencies=[Depends(require_privilege("roles", "update"))],
)
async def restore_role(role_id: UUID, role_service: RoleService = Depends(get_role_service)) -> RoleORM:
    return await role_service.restore_role(role_id)
