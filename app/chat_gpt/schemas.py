from pydantic import BaseModel


class ChatOut(BaseModel):
    id: int
    title: str
    created_at: str

