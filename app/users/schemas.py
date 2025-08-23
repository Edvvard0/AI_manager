from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    name: str
    username: Optional[str] = None
    tg_id: Optional[int] = None
    department: str
    is_admin: bool = False


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    tg_id: Optional[int] = None
    department: Optional[str] = None
    is_admin: Optional[bool] = None