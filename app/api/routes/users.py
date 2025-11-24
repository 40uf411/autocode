from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_user_service, require_privilege
from app.api.schemas import (
    SelfPasswordResetSchema,
    UserCreateSchema,
    UserPasswordResetSchema,
    UserRoleUpdateSchema,
    UserSchema,
    UserSummarySchema,
    UserUpdateSchema,
)
from app.infrastructure.db.repositories import UserORM
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    response_model=List[UserSummarySchema],
    dependencies=[Depends(require_privilege("users", "read"))],
)
async def list_users(
    page: int = 1,
    per_page: int = 50,
    user_service: UserService = Depends(get_user_service),
) -> List[UserSummarySchema]:
    return await user_service.list_users(page=page, per_page=per_page)


@router.post(
    "/",
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_privilege("users", "insert"))],
)
async def create_user(
    payload: UserCreateSchema,
    user_service: UserService = Depends(get_user_service),
) -> UserORM:
    return await user_service.create_user(payload.email, payload.password, payload.role_ids)


@router.patch(
    "/{user_id}",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "update"))],
)
async def update_user(
    user_id: UUID,
    payload: UserUpdateSchema,
    user_service: UserService = Depends(get_user_service),
) -> UserORM:
    return await user_service.update_user(user_id, email=payload.email, role_ids=payload.role_ids)


@router.post(
    "/{user_id}/block",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "block"))],
)
async def block_user(user_id: UUID, user_service: UserService = Depends(get_user_service)) -> UserORM:
    return await user_service.block_user(user_id)


@router.post(
    "/{user_id}/unblock",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "unblock"))],
)
async def unblock_user(user_id: UUID, user_service: UserService = Depends(get_user_service)) -> UserORM:
    return await user_service.unblock_user(user_id)


@router.post(
    "/{user_id}/reset-password",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "reset_password"))],
)
async def reset_user_password(
    user_id: UUID,
    payload: UserPasswordResetSchema,
    user_service: UserService = Depends(get_user_service),
) -> UserORM:
    return await user_service.reset_password(user_id, payload.new_password)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_privilege("users", "delete"))],
)
async def delete_user(
    user_id: UUID,
    hard: bool = False,
    user_service: UserService = Depends(get_user_service),
) -> None:
    await user_service.delete_user(user_id, hard=hard)


@router.post(
    "/{user_id}/restore",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "update"))],
)
async def restore_user(user_id: UUID, user_service: UserService = Depends(get_user_service)) -> UserORM:
    return await user_service.restore_user(user_id)


@router.post(
    "/{user_id}/roles",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "update"))],
)
async def assign_roles(
    user_id: UUID,
    payload: UserRoleUpdateSchema,
    user_service: UserService = Depends(get_user_service),
) -> UserORM:
    return await user_service.assign_roles(user_id, payload.role_ids)


@router.post(
    "/{user_id}/roles/remove",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "update"))],
)
async def remove_roles(
    user_id: UUID,
    payload: UserRoleUpdateSchema,
    user_service: UserService = Depends(get_user_service),
) -> UserORM:
    return await user_service.remove_roles(user_id, payload.role_ids)


@router.get(
    "/count",
    dependencies=[Depends(require_privilege("users", "read"))],
)
async def count_users(user_service: UserService = Depends(get_user_service)) -> dict[str, int]:
    return {"count": await user_service.count_users()}


@router.get(
    "/{user_id}",
    response_model=UserSchema,
    dependencies=[Depends(require_privilege("users", "read"))],
)
async def get_user_detail(user_id: UUID, user_service: UserService = Depends(get_user_service)) -> UserORM:
    return await user_service.get_user_detail(user_id)
