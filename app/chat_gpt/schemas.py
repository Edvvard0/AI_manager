from pydantic import BaseModel


class ChatOut(BaseModel):
    id: int
    title: str
    created_at: str


class SMessageAdd(BaseModel):
    chat_id: int
    content: str