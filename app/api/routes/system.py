from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter

from app.infrastructure.db.base import Base

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/ping")
async def ping() -> dict[str, str | int]:
    now = datetime.now(timezone.utc)
    return {"unix": int(now.timestamp()), "iso": now.isoformat()}


@router.get("/editable-resources")
async def editable_resources() -> dict[str, List[str]]:
    tables: List[str] = []
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__editable__", False):
            tables.append(cls.__tablename__)
    return {"resources": sorted(set(tables))}



@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}