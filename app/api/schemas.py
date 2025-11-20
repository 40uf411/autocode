from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class TokenRequest(BaseModel):
    username: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PrivilegeSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    resource: str
    action: str
    description: Optional[str]


class PrivilegeCreateSchema(BaseModel):
    resource: str
    action: str
    description: Optional[str] = None


class PrivilegeUpdateSchema(BaseModel):
    resource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None


class RoleSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    is_superuser: bool
    privileges: List[PrivilegeSchema]


class RoleSummarySchema(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    is_superuser: bool


class RoleCreateSchema(BaseModel):
    name: str
    is_superuser: bool = False
    privileges: Optional[List[PrivilegeCreateSchema]] = None


class RoleUpdateSchema(BaseModel):
    name: Optional[str] = None
    is_superuser: Optional[bool] = None
    privileges: Optional[List[PrivilegeCreateSchema]] = None


class RolePrivilegeLinkSchema(BaseModel):
    model_config = {"from_attributes": True}

    role_id: int
    role_name: str
    privilege_id: int
    privilege_resource: str
    privilege_action: str
    privilege_description: Optional[str] = None


class RolePrivilegeLinkCreateSchema(BaseModel):
    role_id: int
    privilege_id: int


class UserCreateSchema(BaseModel):
    email: EmailStr
    password: str
    role_ids: Optional[List[int]] = None


class UserSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    is_active: bool
    is_blocked: bool
    created_at: datetime
    roles: List[RoleSchema]


class UserSummarySchema(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    is_active: bool
    is_blocked: bool


class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    role_ids: Optional[List[int]] = None


class UserPasswordResetSchema(BaseModel):
    new_password: str


class SelfPasswordResetSchema(BaseModel):
    old_password: str
    new_password: str


class UserRoleUpdateSchema(BaseModel):
    role_ids: List[int]
