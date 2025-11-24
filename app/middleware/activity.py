import logging
from typing import Optional
from uuid import UUID

import jwt
from fastapi import FastAPI, Request

from app.core.security import decode_access_token
from app.infrastructure.db.repositories import ActivityLogRepository
from app.infrastructure.db.session import get_session_maker


def register_activity_middleware(app: FastAPI) -> None:
    activity_logger = logging.getLogger("user_activity")

    @app.middleware("http")
    async def activity_middleware(request: Request, call_next):
        response = await call_next(request)

        token = request.headers.get("authorization", "")
        user_id: Optional[UUID] = getattr(request.state, "user_id", None)
        if token.lower().startswith("bearer "):
            raw = token.split(" ", 1)[1]
            try:
                payload = decode_access_token(raw)
                user_id = UUID(str(payload.get("sub")))
            except (jwt.PyJWTError, ValueError, TypeError):
                user_id = None

        ip_address = request.headers.get("x-forwarded-for")
        if not ip_address and request.client:
            ip_address = request.client.host

        user_agent = request.headers.get("user-agent")
        client_context = request.headers.get("x-client-context")

        session_factory = get_session_maker()
        try:
            async with session_factory() as session:
                repo = ActivityLogRepository(session)
                await repo.create_log(
                    user_id=user_id,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    client_context=client_context,
                )
                await session.commit()
        except Exception as exc:
            activity_logger.error("Failed to persist activity log: %s", exc, exc_info=True)

        activity_logger.info(
            "%s %s %s %s %s",
            str(user_id) if user_id else "anonymous",
            request.method,
            request.url.path,
            response.status_code,
            ip_address or "unknown",
        )

        return response
