from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_token_blocklist,
    oauth2_scheme,
)
from app.api.schemas import SelfPasswordResetSchema, TokenResponse
from app.infrastructure.db.repositories import UserORM
from app.services.auth_service import AuthService
from app.services.token_service import TokenBlocklistService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    access_token = await auth_service.authenticate(form_data.username, form_data.password)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: UserORM = Depends(get_current_user),
    token_blocklist: TokenBlocklistService = Depends(get_token_blocklist),
) -> dict[str, str]:
    await token_blocklist.revoke(token)
    return {"detail": f"User {current_user.email} logged out"}


@router.post("/reset-password")
async def reset_password(
    payload: SelfPasswordResetSchema,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: UserORM = Depends(get_current_user),
) -> dict[str, str]:
    await auth_service.reset_own_password(current_user, payload.old_password, payload.new_password)
    return {"detail": "Password updated"}
