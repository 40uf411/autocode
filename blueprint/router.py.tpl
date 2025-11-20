from typing import List

from fastapi import APIRouter, Depends

from {{SERVICE_IMPORT}} import business{{CLASS_NAME}}Service
from {{SCHEMA_IMPORT}} import business{{CLASS_NAME}}Read
from app.infrastructure.db.session import get_db_session


router = APIRouter(prefix="/business/{{ROUTE_NAME}}", tags=["business-{{ROUTE_NAME}}"])


@router.get("/", response_model=List[business{{CLASS_NAME}}Read])
async def list_business_{{ROUTE_NAME}}(session=Depends(get_db_session)):
    service = business{{CLASS_NAME}}Service(session)
    return await service.list()


@router.get("/{entity_id:int}", response_model=business{{CLASS_NAME}}Read)
async def get_business_{{ROUTE_NAME}}(entity_id: int, session=Depends(get_db_session)):
    service = business{{CLASS_NAME}}Service(session)
    return await service.get(entity_id)
