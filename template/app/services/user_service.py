from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caching import DragonflyCache, get_cache_backend
from app.infrastructure.db.repositories import UserORM, UserRepository, UserSummary

def _serialize_user(user: UserORM) -> Dict[str, Any]:
    def serialize_privilege(privilege: Any) -> Dict[str, Any]:
        return {
            "id": privilege.id,
            "resource": getattr(privilege, "resource", None),
            "action": getattr(privilege, "action", None),
            "description": getattr(privilege, "description", None),
        }

    def serialize_role(role: Any) -> Dict[str, Any]:
        return {
            "id": role.id,
            "name": getattr(role, "name", None),
            "is_superuser": getattr(role, "is_superuser", False),
            "privileges": [serialize_privilege(p) for p in getattr(role, "privileges", [])],
        }

    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if getattr(user, "updated_at", None) else None,
        "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        "roles": [serialize_role(role) for role in user.roles],
    }


def _deserialize_user(data: Dict[str, Any]) -> SimpleNamespace:
    def parse_dt(value: Optional[str]) -> Optional[datetime]:
        return datetime.fromisoformat(value) if value else None

    def deserialize_privilege(payload: Dict[str, Any]) -> SimpleNamespace:
        return SimpleNamespace(**payload)

    def deserialize_role(payload: Dict[str, Any]) -> SimpleNamespace:
        privileges = [deserialize_privilege(p) for p in payload.get("privileges", [])]
        payload = {**payload, "privileges": privileges}
        return SimpleNamespace(**payload)

    roles = [deserialize_role(role) for role in data.get("roles", [])]
    payload = {
        **data,
        "created_at": parse_dt(data.get("created_at")),
        "updated_at": parse_dt(data.get("updated_at")),
        "deleted_at": parse_dt(data.get("deleted_at")),
        "roles": roles,
    }
    return SimpleNamespace(**payload)


class UserService:
    def __init__(self, session: AsyncSession, cache: Optional[DragonflyCache] = None) -> None:
        self.session = session
        self.cache = cache or get_cache_backend()
        self.repo = UserRepository(session)

    async def get_by_id(self, user_id: int) -> Optional[UserORM]:
        cache_key = f"user:id:{user_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return _deserialize_user(cached)
        user = await self.repo.get_by_id(user_id)
        if user:
            await self.cache.set(cache_key, _serialize_user(user))
        return user

    async def get_by_email(self, email: str) -> Optional[UserORM]:
        cache_key = f"user:email:{email}"
        cached = await self.cache.get(cache_key)
        if cached:
            return _deserialize_user(cached)
        user = await self.repo.get_by_email(email)
        if user:
            await self.cache.set(cache_key, _serialize_user(user))
        return user

    async def create_user(self, email: str, password: str, role_ids: Optional[List[int]]) -> UserORM:
        user = await self.repo.create_user(email=email, password=password, role_ids=role_ids)
        await self._invalidate_cache(user)
        await self.session.commit()
        return await self.repo.get_by_id(user.id) if user.id else user

    async def list_users(self, *, page: int, per_page: int) -> List[UserSummary]:
        per_page = min(max(per_page, 1), 1000)
        page = max(page, 1)
        offset = (page - 1) * per_page
        return await self.repo.list_user_summaries(offset=offset, limit=per_page)

    async def count_users(self) -> int:
        return await self.repo.count_users()

    async def update_user(
        self,
        user_id: int,
        *,
        email: Optional[str] = None,
        role_ids: Optional[List[int]] = None,
    ) -> UserORM:
        user = await self._require_user(user_id, include_deleted=False)
        updated = await self.repo.update_user(user, email=email, role_ids=role_ids)
        await self._invalidate_cache(updated)
        await self.session.commit()
        return updated

    async def block_user(self, user_id: int) -> UserORM:
        user = await self._require_user(user_id)
        updated = await self.repo.set_block_status(user, True)
        await self._invalidate_cache(updated)
        await self.session.commit()
        return updated

    async def unblock_user(self, user_id: int) -> UserORM:
        user = await self._require_user(user_id)
        updated = await self.repo.set_block_status(user, False)
        await self._invalidate_cache(updated)
        await self.session.commit()
        return updated

    async def reset_password(self, user_id: int, new_password: str) -> UserORM:
        user = await self._require_user(user_id)
        updated = await self.repo.reset_password(user, new_password)
        await self._invalidate_cache(updated)
        await self.session.commit()
        return updated

    async def delete_user(self, user_id: int, *, hard: bool = False) -> None:
        user = await self._require_user(user_id, include_deleted=True)
        if hard:
            await self.repo.hard_delete(user)
        else:
            await self.repo.soft_delete(user)
        await self._invalidate_cache(user)
        await self.session.commit()

    async def restore_user(self, user_id: int) -> UserORM:
        user = await self._require_user(user_id, include_deleted=True)
        if user.deleted_at is None:
            return user
        restored = await self.repo.restore(user)
        await self._invalidate_cache(restored)
        await self.session.commit()
        return restored

    async def assign_roles(self, user_id: int, role_ids: List[int]) -> UserORM:
        user = await self._require_user(user_id)
        await self.repo.attach_roles(user, role_ids)
        await self._invalidate_cache(user)
        await self.session.commit()
        return await self.repo.get_detailed_by_id(user_id)

    async def remove_roles(self, user_id: int, role_ids: List[int]) -> UserORM:
        user = await self._require_user(user_id)
        await self.repo.detach_roles(user, role_ids)
        await self._invalidate_cache(user)
        await self.session.commit()
        return await self.repo.get_by_id(user_id)

    async def get_user_detail(self, user_id: int) -> UserORM:
        user = await self.repo.get_detailed_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _invalidate_cache(self, user: Optional[UserORM]) -> None:
        if not user:
            return
        await self.cache.delete(f"user:email:{user.email}")
        if user.id:
            await self.cache.delete(f"user:id:{user.id}")

    async def _require_user(self, user_id: int, include_deleted: bool = False) -> UserORM:
        user = (
            await self.repo.get_by_id_include_deleted(user_id)
            if include_deleted
            else await self.repo.get_by_id(user_id)
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not include_deleted and user.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
