from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class business{{CLASS_NAME}}Base(BaseModel):
{{SCHEMA_FIELDS}}


class business{{CLASS_NAME}}Create(business{{CLASS_NAME}}Base):
    pass


class business{{CLASS_NAME}}Read(business{{CLASS_NAME}}Base):
    id: UUID
    created_at: Optional[datetime] = None
