from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PermissionBase(BaseModel):
    name: str

class RoleBase(BaseModel):
    name: str

class DepartmentBase(BaseModel):
    name: str

class UserBase(BaseModel):
    username: str
    email: str
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
