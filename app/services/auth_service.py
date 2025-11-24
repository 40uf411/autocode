from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.infrastructure.db.repositories import UserORM, UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate(self, email: str, password: str) -> str:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if user.is_blocked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return token

    async def assert_privilege(self, user_id: UUID, resource: str, action: str) -> None:
        if await self.user_repo.user_is_superuser(user_id):
            return
        has_permission = await self.user_repo.user_has_privilege(user_id, resource, action)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing privilege {action} on {resource}",
            )

    async def reset_own_password(self, user: UserORM, old_password: str, new_password: str) -> None:
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password")
        await self.user_repo.reset_password(user, new_password)
        await self.session.commit()
