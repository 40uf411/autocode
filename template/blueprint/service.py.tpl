from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from {{REPOSITORY_IMPORT}} import Custom{{CLASS_NAME}}Repository


class Custom{{CLASS_NAME}}Service:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = Custom{{CLASS_NAME}}Repository(session)

    async def list(self) -> List:
        return await self.repo.list()

    async def get(self, entity_id: int) -> Optional:
        return await self.repo.get(entity_id)
