from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from {{MODEL_MODULE}} import {{ORM_CLASS}}


class business{{CLASS_NAME}}Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> List[{{ORM_CLASS}}]:
        result = await self.session.execute(select({{ORM_CLASS}}))
        return result.scalars().all()

    async def get(self, entity_id: UUID) -> Optional[{{ORM_CLASS}}]:
        result = await self.session.execute(select({{ORM_CLASS}}).where({{ORM_CLASS}}.id == entity_id))
        return result.scalar_one_or_none()
