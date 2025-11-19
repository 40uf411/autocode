import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, privileges, roles, system, users
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.db.seeds import seed_initial_data
from app.infrastructure.db.session import init_db
from app.middleware.activity import register_activity_middleware

settings = get_settings()
configure_logging()
server_logger = logging.getLogger("server")


@asynccontextmanager
async def lifespan(_: FastAPI):
    server_logger.info("Starting application")
    await init_db()
    await seed_initial_data()
    yield
    server_logger.info("Shutting down application")


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
register_activity_middleware(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(privileges.router)
app.include_router(system.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
