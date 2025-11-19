from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.db.repositories import {{ORM_IMPORT}}


class Custom{{CLASS_NAME}}Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> List[{{CLASS_NAME}}ORM]:
        result = await self.session.execute(select({{CLASS_NAME}}ORM))
        return result.scalars().all()

    async def get(self, entity_id: int) -> Optional[{{CLASS_NAME}}ORM]:
        result = await self.session.execute(select({{CLASS_NAME}}ORM).where({{CLASS_NAME}}ORM.id == entity_id))
        return result.scalar_one_or_none()
