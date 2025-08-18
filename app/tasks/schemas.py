
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str
    description: str
    deadline_date: date
    executor_id: Optional[int] = None

    chat_id: Optional[int] = None

    status: str = Field(default="Начал")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline_date: Optional[date] = None
    executor_id: Optional[int] = None
    chat_id: Optional[int] = None

    status: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    deadline_date: date
    executor_id: Optional[int]

    chat_id: Optional[int] = None

    status: str
    comment: Optional[str] = None
    file_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)