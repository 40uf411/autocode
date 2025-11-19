from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class BaseDomain:
    id: Optional[int]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


@dataclass
class Privilege(BaseDomain):
    resource: str
    action: str
    description: Optional[str] = None


@dataclass
class Role(BaseDomain):
    name: str
    privileges: List[Privilege]


@dataclass
class User(BaseDomain):
    email: str
    hashed_password: str
    is_active: bool
    is_blocked: bool
    roles: List[Role]
