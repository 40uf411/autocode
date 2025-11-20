from typing import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.infrastructure.db.repositories import UserORM
from app.infrastructure.db.session import get_db_session
from app.services.auth_service import AuthService
from app.services.privilege_service import PrivilegeService
from app.services.role_service import RoleService
from app.services.token_service import TokenBlocklistService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UserService:
    return UserService(session)


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuthService:
    return AuthService(session)


async def get_role_service(
    session: AsyncSession = Depends(get_db_session),
) -> RoleService:
    return RoleService(session)


async def get_token_blocklist() -> TokenBlocklistService:
    return TokenBlocklistService()


async def get_privilege_service(
    session: AsyncSession = Depends(get_db_session),
) -> PrivilegeService:
    return PrivilegeService(session)


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
    token_blocklist: TokenBlocklistService = Depends(get_token_blocklist),
) -> UserORM:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_exception
    if await token_blocklist.is_revoked(token):
        raise credentials_exception
    user = await user_service.get_by_id(user_id)
    if not user or user.is_blocked:
        raise credentials_exception
    if request is not None:
        request.state.user_id = user.id
    return user


def require_privilege(resource: str, action: str) -> Callable[[UserORM, AuthService], UserORM]:
    async def dependency(
        current_user: UserORM = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> UserORM:
        await auth_service.assert_privilege(current_user.id, resource, action)
        return current_user

    return dependency


async def require_superuser(
    current_user: UserORM = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserORM:
    if await auth_service.user_repo.user_is_superuser(current_user.id):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superuser privileges required",
    )
