from typing import List

from fastapi import APIRouter, Depends

from {{SERVICE_IMPORT}} import Custom{{CLASS_NAME}}Service
from {{SCHEMA_IMPORT}} import Custom{{CLASS_NAME}}Read
from app.infrastructure.db.session import get_db_session


router = APIRouter(prefix="/custom/{{ROUTE_NAME}}", tags=["custom-{{ROUTE_NAME}}"])


@router.get("/", response_model=List[Custom{{CLASS_NAME}}Read])
async def list_custom_{{ROUTE_NAME}}(session=Depends(get_db_session)):
    service = Custom{{CLASS_NAME}}Service(session)
    return await service.list()


@router.get("/{entity_id}", response_model=Custom{{CLASS_NAME}}Read)
async def get_custom_{{ROUTE_NAME}}(entity_id: int, session=Depends(get_db_session)):
    service = Custom{{CLASS_NAME}}Service(session)
    return await service.get(entity_id)
