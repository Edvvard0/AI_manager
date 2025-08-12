from pydantic import BaseModel, EmailStr


class SUser(BaseModel):
    id: int
    name: str
    tg_id: id
    department: str


class SUserAdd(BaseModel):
    name: str
    tg_id: id
    department: str
