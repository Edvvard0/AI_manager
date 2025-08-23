from pydantic import BaseModel


class SUser(BaseModel):
    id: int
    name: str
    username: str
    tg_id: int
    department: str
    is_admin: bool


class SUserAdd(BaseModel):
    name: str
    username: str
    tg_id: int
    department: str
    is_admin: bool
