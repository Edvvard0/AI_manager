from datetime import datetime

from pydantic import BaseModel


class ChatOut(BaseModel):
    id: int
    title: str
    created_at: datetime


class SMessageAdd(BaseModel):
    chat_id: int
    content: str


class STaskAddGPT(BaseModel):
    title: str
    description: str
