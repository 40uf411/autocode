from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_privilege_service, require_privilege
from app.api.schemas import (
    PrivilegeCreateSchema,
    PrivilegeSchema,
    PrivilegeUpdateSchema,
)
from app.infrastructure.db.repositories import PrivilegeORM
from app.services.privilege_service import PrivilegeService

router = APIRouter(prefix="/privileges", tags=["privileges"])


@router.get(
    "/",
    response_model=List[PrivilegeSchema],
    dependencies=[Depends(require_privilege("privileges", "read"))],
)
async def list_privileges(
    page: int = 1,
    per_page: int = 50,
    privilege_service: PrivilegeService = Depends(get_privilege_service),
) -> List[PrivilegeORM]:
    return await privilege_service.list_privileges(page=page, per_page=per_page)


@router.get(
    "/count",
    dependencies=[Depends(require_privilege("privileges", "read"))],
)
async def count_privileges(
    privilege_service: PrivilegeService = Depends(get_privilege_service),
) -> dict[str, int]:
    return {"count": await privilege_service.count()}


@router.post(
    "/",
    response_model=PrivilegeSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_privilege("privileges", "insert"))],
)
async def create_privilege(
    payload: PrivilegeCreateSchema,
    privilege_service: PrivilegeService = Depends(get_privilege_service),
) -> PrivilegeORM:
    return await privilege_service.create_privilege(payload.resource, payload.action, payload.description)


@router.patch(
    "/{privilege_id}",
    response_model=PrivilegeSchema,
    dependencies=[Depends(require_privilege("privileges", "update"))],
)
async def update_privilege(
    privilege_id: UUID,
    payload: PrivilegeUpdateSchema,
    privilege_service: PrivilegeService = Depends(get_privilege_service),
) -> PrivilegeORM:
    return await privilege_service.update_privilege(
        privilege_id,
        resource=payload.resource,
        action=payload.action,
        description=payload.description,
    )


@router.delete(
    "/{privilege_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_privilege("privileges", "delete"))],
)
async def delete_privilege(
    privilege_id: UUID,
    hard: bool = False,
    privilege_service: PrivilegeService = Depends(get_privilege_service),
) -> None:
    await privilege_service.delete_privilege(privilege_id, hard=hard)


@router.post(
    "/{privilege_id}/restore",
    response_model=PrivilegeSchema,
    dependencies=[Depends(require_privilege("privileges", "update"))],
)
async def restore_privilege(
    privilege_id: UUID,
    privilege_service: PrivilegeService = Depends(get_privilege_service),
) -> PrivilegeORM:
    return await privilege_service.restore_privilege(privilege_id)
