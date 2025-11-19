from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Custom{{CLASS_NAME}}Base(BaseModel):
{{SCHEMA_FIELDS}}


class Custom{{CLASS_NAME}}Create(Custom{{CLASS_NAME}}Base):
    pass


class Custom{{CLASS_NAME}}Read(Custom{{CLASS_NAME}}Base):
    id: int
    created_at: Optional[datetime] = None
