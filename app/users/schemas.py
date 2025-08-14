from pydantic import BaseModel, EmailStr


class SUser(BaseModel):
    id: int
    name: str
    tg_id: id
    department: str
    is_admin: bool


class SUserAdd(BaseModel):
    name: str
    tg_id: id
    department: str
    is_admin: bool
