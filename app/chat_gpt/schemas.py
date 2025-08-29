from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChatOut(BaseModel):
    id: int
    title: str
    created_at: datetime


class SMessageAdd(BaseModel):
    chat_id: int
    content: str


class SFirstMessage(BaseModel):
    content: str
    tg_id: int
    project_id: Optional[int] = None


class STaskAddGPT(BaseModel):
    title: str
    description: str


class PromptResponse(BaseModel):
    response: str


class AnswerResponse(BaseModel):
    answer: str


class ChatMessageSearchOut(BaseModel):
    chat_id: int
    chat_title: str
    message_id: Optional[int] = None
    message_content: Optional[str] = None
    rank: float



class ChatSearchResult(BaseModel):
    chat_id: int
    chat_title: str
    message_id: Optional[int] = None
    message_content: Optional[str] = None
    # rank: float


class MinutesResponse(BaseModel):
    protocol: str
    # detected_command: bool
    # transcript_preview: str